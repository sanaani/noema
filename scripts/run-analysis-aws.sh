#!/bin/bash
# Run the published forward analyses against the unseeded corpus, on a
# temporary AWS CPU worker.
#
# Not a laptop job: 11,489 centroids make a 66-million-pair upper triangle, the
# angle matrix alone is a gigabyte, and the eligibility test walks every pair in
# Python. None of the analysis code changes -- these are phase 1's scripts with
# phase 2's inputs, which is the entire point of the comparison.
#
# About $0.30: an m6i.4xlarge for twenty minutes.
#
#   scripts/run-analysis-aws.sh launch <vectors.npz> <text-index.jsonl.gz>
#   scripts/run-analysis-aws.sh watch    <run-name>
#   scripts/run-analysis-aws.sh fetch    <run-name>
#   scripts/run-analysis-aws.sh teardown <run-name>
set -euo pipefail

REGION=us-east-2
BUCKET=noema-structural-gpu-159976616274-20260917t220221z
INSTANCE_TYPE=m6i.4xlarge
AMI=ami-00adec9774170bad2                 # Ubuntu 24.04, us-east-2
REPO="$(cd "$(dirname "$0")/.." && pwd)"
# Phase 3 overrides this.
OUTROOT="${OUTROOT:-$REPO/outputs/phase-2-dependency-labels}"

launch() {
  local vectors=${1:?path to reprover-embeddings.npz}
  local index=${2:?path to text-index.jsonl.gz}
  local run ts
  ts=$(date -u +%Y%m%d-%H%M%S)
  run="noema-analysis-$ts"
  local out="$OUTROOT/$run"
  mkdir -p "$out/task/noema/in"

  echo "== packaging the task"
  cp "$vectors" "$out/task/noema/in/reprover-embeddings.npz"
  cp "$index" "$out/task/noema/in/text-index.jsonl.gz"
  cp -r "$REPO/scripts" "$out/task/noema/scripts"
  cp -r "$REPO/src" "$out/task/noema/src"
  mkdir -p "$out/task/noema/results/phase-2-dependency-labels"
  cp -r "$REPO/results/phase-1-recognition" "$out/task/noema/results/phase-1-recognition"
  cp -r "$REPO/results/phase-2-dependency-labels/unseeded-corpus-v1" \
        "$REPO/results/phase-2-dependency-labels/link-graph-2026-v1" \
        "$out/task/noema/results/phase-2-dependency-labels/"
  find "$out/task" \( -name __pycache__ -o -name '*.pyc' \) -exec rm -rf {} + 2>/dev/null || true
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
    --tags Key=Project,Value=noema Key=Purpose,Value=temporary-analysis >/dev/null
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
        --description "temporary noema analysis worker" --vpc-id "$vpc" \
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
      "$REPO/scripts/analysis-user-data.sh.in" > "$out/user-data.sh"

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
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$run},{Key=Project,Value=noema},{Key=Purpose,Value=temporary-analysis}]" \
    --user-data "file://$out/user-data.sh" \
    --query 'Instances[0].InstanceId' --output text)
  echo "$id" > "$out/instance-id"
  echo "$sg"  > "$out/security-group-id"
  echo
  echo "run       $run"
  echo "instance  $id  ($INSTANCE_TYPE, self-terminating)"
  echo "artifacts $out"
  echo
  echo "watch:    scripts/run-analysis-aws.sh watch $run"
}

watch_run() {
  local run=$1 out="$OUTROOT/$1"
  local id; id=$(cat "$out/instance-id")
  echo "instance state : $(aws ec2 describe-instances --region "$REGION" --instance-ids "$id" \
        --query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null || echo gone)"
  echo "console:"
  aws ec2 get-console-output --region "$REGION" --instance-id "$id" --latest \
    --query Output --output text 2>/dev/null \
    | grep -E "(boot|STAGE|ALIVE|JOB DONE|FINISH|AUC)" | tail -10
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
  launch)   launch "${2:?vectors.npz}" "${3:?text-index.jsonl.gz}" ;;
  watch)    watch_run "${2:?run name}" ;;
  fetch)    fetch "${2:?run name}" ;;
  teardown) teardown "${2:?run name}" ;;
  *) sed -n '2,17p' "$0"; exit 2 ;;
esac
