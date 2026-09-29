#!/bin/bash
# Phase 12 on a temporary AWS CPU worker.
#
# The worker runs scripts/run-phase12.py (every setting fixed in the phase 12
# README) on Phase 11's papers and references: author ids from the OpenAlex
# snapshot, then the ladder analysis. Smoke pass first. The instance
# terminates on shutdown and a 2-hour timer backs that up.
#
#   scripts/run-phase12-aws.sh launch
#   scripts/run-phase12-aws.sh watch    <run-name>
#   scripts/run-phase12-aws.sh fetch    <run-name>
#   scripts/run-phase12-aws.sh teardown <run-name>
set -euo pipefail

REGION=us-east-2
BUCKET=noema-structural-gpu-159976616274-20260917t220221z
# In preference order. g6e is an L40S, which is what phase 3 encoded on; the
# rest are 24 GB cards that comfortably hold this corpus now that no state runs
# past 8,192 bytes. GPU capacity is scarce and per availability zone, so the
# launcher walks types and zones rather than failing on the first refusal.
INSTANCE_TYPES="m6i.4xlarge m7i.4xlarge m6a.4xlarge r6i.2xlarge"
AMI=ami-032e2f7bde5ba7967              # Deep Learning base, us-east-2
REPO="$(cd "$(dirname "$0")/.." && pwd)"
OUTROOT="${OUTROOT:-$REPO/outputs/phase-12-closeness-ladder}"

launch() {
  local run ts
  ts=$(date -u +%Y%m%d-%H%M%S)
  run="noema-p12-$ts"
  local out="$OUTROOT/$run"
  local t="$out/task/noema"
  mkdir -p "$t/scripts"

  echo "== packaging the task"
  cp "$REPO/scripts/run-phase11.py" "$REPO/scripts/run-phase12.py" \
     "$REPO/scripts/count-horizons.py" "$REPO/scripts/run-phase13.py" \
     "$REPO/scripts/run-phase14.py" "$t/scripts/"
  # Phase 11's papers, references and snapshot file list
  local data="$REPO/outputs/phase-11-tool-area-grid/data"
  mkdir -p "$t/in"
  cp "$data/papers.jsonl.gz" "$data/refs.jsonl.gz" "$data/works-files.txt" "$t/in/"
  # USERDATA=horizons (the watch-length count) or phase13: from saved author ids
  if [ -n "${USERDATA:-}" ]; then cp "$data/authors.jsonl.gz" "$t/in/"; fi
  ( cd "$t" && find . -type f -exec sha256sum {} + > "$out/task-SHA256SUMS" )
  tar czf "$out/task.tar.gz" -C "$out/task" noema
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
    --tags Key=Project,Value=noema Key=Purpose,Value=temporary-phase12-cpu >/dev/null
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
        --description "temporary noema phase 12 worker" --vpc-id "$vpc" \
        --query GroupId --output text)
  aws ec2 revoke-security-group-egress --region "$REGION" --group-id "$sg" \
    --protocol -1 --port -1 --cidr 0.0.0.0/0 >/dev/null 2>&1 || true
  aws ec2 authorize-security-group-egress --region "$REGION" --group-id "$sg" \
    --protocol tcp --port 443 --cidr 0.0.0.0/0 >/dev/null
  aws ec2 authorize-security-group-egress --region "$REGION" --group-id "$sg" \
    --protocol tcp --port 80 --cidr 0.0.0.0/0 >/dev/null
  # Every default subnet, not just the first: GPU capacity runs out per
  # availability zone, and one zone being full says nothing about the next.
  local subnets
  subnets=$(aws ec2 describe-subnets --region "$REGION" \
            --filters Name=vpc-id,Values="$vpc" Name=default-for-az,Values=true \
            --query 'Subnets[].SubnetId' --output text)

  echo "== user data"
  sed -e "s|@BUCKET@|$BUCKET|g" -e "s|@RUN@|$run|g" \
      "$REPO/scripts/$(case "${USERDATA:-}" in phase1[34]) echo "$USERDATA" ;; *) echo "phase12${USERDATA:+-$USERDATA}" ;; esac)-user-data.sh.in" > "$out/user-data.sh"

  echo "== waiting for the instance profile to propagate"
  sleep 20

  local id="" itype=""
  for itype in $INSTANCE_TYPES; do
   for subnet in $subnets; do
    echo "== trying $itype in $subnet"
   id=$(aws ec2 run-instances --region "$REGION" \
    --image-id "$AMI" --instance-type "$itype" --count 1 \
    --iam-instance-profile "Name=$run" \
    --instance-initiated-shutdown-behavior terminate \
    --metadata-options 'HttpTokens=required,HttpEndpoint=enabled,HttpPutResponseHopLimit=1' \
    --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":100,"VolumeType":"gp3","Encrypted":true,"DeleteOnTermination":true}}]' \
    --network-interfaces "[{\"DeviceIndex\":0,\"SubnetId\":\"$subnet\",\"Groups\":[\"$sg\"],\"AssociatePublicIpAddress\":true,\"DeleteOnTermination\":true}]" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$run},{Key=Project,Value=noema},{Key=Purpose,Value=temporary-phase12-cpu}]" \
    --user-data "file://$out/user-data.sh" \
    --query 'Instances[0].InstanceId' --output text 2>"$out/launch-error.txt") || id=""
    [ -n "$id" ] && [ "$id" != "None" ] && break
    echo "   $(tail -1 "$out/launch-error.txt" | grep -o 'InsufficientInstanceCapacity\|[A-Za-z]*Error' | head -1)"
   done
   [ -n "$id" ] && [ "$id" != "None" ] && break
  done
  if [ -z "$id" ] || [ "$id" = "None" ]; then
    echo "no zone had capacity for any of: $INSTANCE_TYPES"
    echo "teardown $run and retry later, or add a type"
    return 1
  fi
  echo "$itype" > "$out/instance-type"
  echo "$id" > "$out/instance-id"
  echo "$sg"  > "$out/security-group-id"
  echo
  echo "run       $run"
  echo "instance  $id  ($itype, self-terminating)"
  echo "artifacts $out"
  echo
  echo "watch:    scripts/run-phase12-aws.sh watch $run"
}

watch_run() {
  local run=$1 out="$OUTROOT/$1"
  local id; id=$(cat "$out/instance-id")
  echo "instance state : $(aws ec2 describe-instances --region "$REGION" --instance-ids "$id" \
        --query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null || echo gone)"
  echo "console:"
  aws ec2 get-console-output --region "$REGION" --instance-id "$id" --latest \
    --query Output --output text 2>/dev/null \
    | grep -E "(boot|pydeps-done|STAGE|snapshot|fit:|test:|H1|SMOKE|UPLOADED|JOB DONE|FINISH|Error|Traceback)" | tail -12
  echo "s3:"
  aws s3 ls "s3://$BUCKET/results/$run/" --region "$REGION" 2>/dev/null || echo "  (not yet)"
}

fetch() {
  local run=$1 out="$OUTROOT/$1"
  aws s3 cp "s3://$BUCKET/results/$run/result.tar.gz" "$out/result.tar.gz" --region "$REGION"
  tar xzf "$out/result.tar.gz" -C "$out"
  find "$out/noema/out" -type f | sed 's/^/  /'
}

teardown() {
  local run=$1 out="$OUTROOT/$1"
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
  fetch)    fetch "${2:?run name}" ;;
  teardown) teardown "${2:?run name}" ;;
  *) sed -n '2,14p' "$0"; exit 2 ;;
esac
