#!/bin/bash
# Capture proof states for the pre-registered unseeded corpus, on a temporary
# AWS CPU worker.
#
# Phase 1's corpus was chosen theorem by theorem, which leaves a selection
# effect no analysis can remove. Phase 2 replaces it with 350 files drawn once
# from a committed seed (results/phase-2-dependency-labels/unseeded-corpus-v1/).
# This script captures the proof states for that draw, in the same Lean 4.9.0 /
# Mathlib f0957a7 / patched-REPL environment phase 1 used, so the new centroids
# are comparable with the old ones.
#
# The run is staged and the throughput gates the spend: it replays a random
# dozen files first, measures seconds per file, projects the rest, and only
# continues if the projection fits MAX_REPLAY_HOURS. Over budget, it ships the
# probe and terminates.
#
# Every resource is tagged for this run and removed by `teardown`. The instance
# terminates itself three independent ways.
#
#   scripts/run-capture-aws.sh launch
#   scripts/run-capture-aws.sh watch    <run-name>
#   scripts/run-capture-aws.sh probe    <run-name>   # the measurement, once it lands
#   scripts/run-capture-aws.sh shell    <run-name>   # Session Manager, no SSH
#   scripts/run-capture-aws.sh fetch    <run-name>
#   scripts/run-capture-aws.sh teardown <run-name>
set -euo pipefail

REGION=us-east-2
BUCKET=noema-structural-gpu-159976616274-20260917t220221z
INSTANCE_TYPE=m6i.4xlarge
AMI=ami-00adec9774170bad2                 # Ubuntu 24.04, us-east-2
PROBE_FILES=18
MAX_REPLAY_HOURS=3.0
REPO="$(cd "$(dirname "$0")/.." && pwd)"
CORPUS="$REPO/results/phase-2-dependency-labels/unseeded-corpus-v1"

launch() {
  local run ts
  ts=$(date -u +%Y%m%d-%H%M%S)
  run="noema-capture-$ts"
  local out="$REPO/outputs/phase-2-dependency-labels/$run"
  mkdir -p "$out/task/corpus" "$out/task/scripts" "$out/task/state-object-patches"

  echo "== packaging the task"
  cp "$CORPUS/modules.txt" "$CORPUS/names.txt" "$CORPUS/sample.json" "$out/task/corpus/"
  cp "$REPO/results/phase-1-recognition/link-graph-v1/DeclRanges.lean" "$out/task/"
  cp "$REPO/scripts/build-state-bridge-selection.py" \
     "$REPO/scripts/replay-state-object-mathlib.py" "$out/task/scripts/"
  cp "$REPO/scripts/state-object-patches/repl-d920817-noema.patch" \
     "$out/task/state-object-patches/"
  cp -r "$REPO/src" "$out/task/src"
  find "$out/task/src" -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
  tar czf "$out/task.tar.gz" -C "$out/task" .
  aws s3 cp "$out/task.tar.gz" "s3://$BUCKET/$run-task.tar.gz" --region "$REGION"

  echo "== IAM role, scoped to this run's keys"
  cat > "$out/trust.json" <<'JSON'
{"Version":"2012-10-17","Statement":[{"Effect":"Allow",
 "Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}
JSON
  cat > "$out/policy.json" <<JSON
{"Version":"2012-10-17","Statement":[
 {"Effect":"Allow","Action":["s3:GetObject"],
  "Resource":["arn:aws:s3:::$BUCKET/$run-task.tar.gz"]},
 {"Effect":"Allow","Action":["s3:PutObject"],
  "Resource":["arn:aws:s3:::$BUCKET/results/$run/*"]}]}
JSON
  aws iam create-role --role-name "$run" \
    --assume-role-policy-document "file://$out/trust.json" \
    --tags Key=Project,Value=noema Key=Purpose,Value=temporary-state-capture >/dev/null
  aws iam put-role-policy --role-name "$run" --policy-name s3-temp \
    --policy-document "file://$out/policy.json"
  # Baked in at role creation, not attached later: by the time a run looks
  # stuck the SSM agent has already backed off and will not pick up a new
  # policy. This is the only way in without an ingress rule.
  aws iam attach-role-policy --role-name "$run" \
    --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
  aws iam create-instance-profile --instance-profile-name "$run" >/dev/null
  aws iam add-role-to-instance-profile --instance-profile-name "$run" --role-name "$run"

  echo "== security group, egress only"
  local vpc sg subnet
  vpc=$(aws ec2 describe-vpcs --region "$REGION" --filters Name=isDefault,Values=true \
        --query 'Vpcs[0].VpcId' --output text)
  sg=$(aws ec2 create-security-group --region "$REGION" --group-name "$run" \
        --description "temporary noema capture worker" --vpc-id "$vpc" \
        --query GroupId --output text)
  aws ec2 revoke-security-group-egress --region "$REGION" --group-id "$sg" \
    --protocol -1 --port -1 --cidr 0.0.0.0/0 >/dev/null 2>&1 || true
  aws ec2 authorize-security-group-egress --region "$REGION" --group-id "$sg" \
    --protocol tcp --port 443 --cidr 0.0.0.0/0 >/dev/null
  aws ec2 authorize-security-group-egress --region "$REGION" --group-id "$sg" \
    --protocol tcp --port 80 --cidr 0.0.0.0/0 >/dev/null
  subnet=$(aws ec2 describe-subnets --region "$REGION" \
            --filters Name=vpc-id,Values="$vpc" Name=default-for-az,Values=true \
            --query 'Subnets[0].SubnetId' --output text)

  echo "== user data"
  sed -e "s|@BUCKET@|$BUCKET|g" -e "s|@RUN@|$run|g" \
      -e "s|@PROBE@|$PROBE_FILES|g" -e "s|@MAX_REPLAY_HOURS@|$MAX_REPLAY_HOURS|g" \
      "$REPO/scripts/capture-user-data.sh.in" > "$out/user-data.sh"

  echo "== waiting for the instance profile to propagate"
  sleep 20

  local id
  id=$(aws ec2 run-instances --region "$REGION" \
    --image-id "$AMI" --instance-type "$INSTANCE_TYPE" --count 1 \
    --iam-instance-profile "Name=$run" \
    --instance-initiated-shutdown-behavior terminate \
    --metadata-options 'HttpTokens=required,HttpEndpoint=enabled,HttpPutResponseHopLimit=1' \
    --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":200,"VolumeType":"gp3","Encrypted":true,"DeleteOnTermination":true}}]' \
    --network-interfaces "[{\"DeviceIndex\":0,\"SubnetId\":\"$subnet\",\"Groups\":[\"$sg\"],\"AssociatePublicIpAddress\":true,\"DeleteOnTermination\":true}]" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$run},{Key=Project,Value=noema},{Key=Purpose,Value=temporary-state-capture}]" \
    --user-data "file://$out/user-data.sh" \
    --query 'Instances[0].InstanceId' --output text)
  echo "$id" > "$out/instance-id"
  echo "$sg"  > "$out/security-group-id"
  echo
  echo "run       $run"
  echo "instance  $id  ($INSTANCE_TYPE, self-terminating)"
  echo "gate      probe $PROBE_FILES files, continue only under $MAX_REPLAY_HOURS h"
  echo "artifacts $out"
  echo
  echo "watch:    scripts/run-capture-aws.sh watch $run"
}

watch_run() {
  local run=$1 out="$REPO/outputs/phase-2-dependency-labels/$1"
  local id; id=$(cat "$out/instance-id")
  echo "instance state : $(aws ec2 describe-instances --region "$REGION" --instance-ids "$id" \
        --query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null || echo gone)"
  echo "console:"
  aws ec2 get-console-output --region "$REGION" --instance-id "$id" --latest \
    --query Output --output text 2>/dev/null \
    | grep -E "(STAGE|HARVEST|ALIVE|FINISH|JOB DONE|oleans|ranges:|probe:|full:)" | tail -8
  echo "s3:"
  aws s3 ls "s3://$BUCKET/results/$run/" --region "$REGION" 2>/dev/null || echo "  (not yet)"
}

# The measurement, pulled out on its own: this is what decides whether the run
# continues, so it should be readable without unpacking a tarball.
probe_report() {
  local run=$1 out="$REPO/outputs/phase-2-dependency-labels/$1"
  aws s3 cp "s3://$BUCKET/results/$run/probe.tar.gz" "$out/probe.tar.gz" --region "$REGION"
  tar xOzf "$out/probe.tar.gz" noema/out/probe-report.json
}

shell_run() {
  local run=$1 out="$REPO/outputs/phase-2-dependency-labels/$1"
  local id ping; id=$(cat "$out/instance-id")
  ping=$(aws ssm describe-instance-information --region "$REGION" \
    --filters "Key=InstanceIds,Values=$id" \
    --query 'InstanceInformationList[0].PingStatus' --output text 2>/dev/null)
  if [ "$ping" != "Online" ]; then
    echo "instance $id is not registered with SSM (ping=${ping:-none}); use 'watch'."
    return 1
  fi
  aws ssm start-session --region "$REGION" --target "$id"
}

fetch() {
  local run=$1 out="$REPO/outputs/phase-2-dependency-labels/$1"
  aws s3 cp "s3://$BUCKET/results/$run/result.tar.gz" "$out/result.tar.gz" --region "$REGION"
  tar xzf "$out/result.tar.gz" -C "$out"
  find "$out/noema/out" -maxdepth 1 -type f | sed 's/^/  /'
}

teardown() {
  local run=$1 out="$REPO/outputs/phase-2-dependency-labels/$1"
  local id sg
  id=$(cat "$out/instance-id" 2>/dev/null || true)
  sg=$(cat "$out/security-group-id" 2>/dev/null || true)
  [ -n "$id" ] && aws ec2 terminate-instances --region "$REGION" --instance-ids "$id" \
      --query 'TerminatingInstances[0].CurrentState.Name' --output text || true
  [ -n "$id" ] && aws ec2 wait instance-terminated --region "$REGION" --instance-ids "$id" || true
  [ -n "$sg" ] && aws ec2 delete-security-group --region "$REGION" --group-id "$sg" || true
  aws iam remove-role-from-instance-profile --instance-profile-name "$run" --role-name "$run" || true
  aws iam delete-instance-profile --instance-profile-name "$run" || true
  aws iam delete-role-policy --role-name "$run" --policy-name s3-temp || true
  aws iam detach-role-policy --role-name "$run" \
    --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore || true
  aws iam delete-role --role-name "$run" || true
  aws s3 rm "s3://$BUCKET/$run-task.tar.gz" --region "$REGION" || true
  echo "torn down: $run"
}

case "${1:-}" in
  launch)   launch ;;
  watch)    watch_run "${2:?run name}" ;;
  probe)    probe_report "${2:?run name}" ;;
  shell)    shell_run "${2:?run name}" ;;
  fetch)    fetch "${2:?run name}" ;;
  teardown) teardown "${2:?run name}" ;;
  *) sed -n '2,28p' "$0"; exit 2 ;;
esac
