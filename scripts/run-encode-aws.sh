#!/bin/bash
# Encode a frozen state-text list with the pinned ReProver retriever, on a
# temporary AWS GPU worker.
#
# The encoder is the one phase 1 used and it verifies that itself: it refuses
# to run unless the acquisition source hashes and the model/runtime manifest
# match what `build-encode-inputs.py` froze. That is what makes the phase 2
# centroids comparable with the phase 1 ones -- the corpus moves, the encoder
# does not.
#
# Roughly $0.60 for a corpus this size: a g6e.xlarge at ~$1.86/hr, twenty
# minutes including the driver warm-up and the model fetch.
#
#   scripts/run-encode-aws.sh launch <inputs.json>
#   scripts/run-encode-aws.sh watch    <run-name>
#   scripts/run-encode-aws.sh fetch    <run-name>
#   scripts/run-encode-aws.sh teardown <run-name>
set -euo pipefail

REGION=us-east-2
BUCKET=noema-structural-gpu-159976616274-20260917t220221z
# In preference order. g6e is an L40S, which is what phase 1 encoded on; the
# rest are 24 GB cards that comfortably hold this corpus now that no state runs
# past 8,192 bytes. GPU capacity is scarce and per availability zone, so the
# launcher walks types and zones rather than failing on the first refusal.
INSTANCE_TYPES="g6e.xlarge g6.2xlarge g5.2xlarge g6.xlarge g5.xlarge"
AMI=ami-032e2f7bde5ba7967              # Deep Learning base, us-east-2
REPO="$(cd "$(dirname "$0")/.." && pwd)"

launch() {
  local inputs=${1:?path to inputs.json}
  local run ts
  ts=$(date -u +%Y%m%d-%H%M%S)
  run="noema-encode-$ts"
  local out="$REPO/outputs/phase-2-dependency-labels/$run"
  mkdir -p "$out/task/noema/in" "$out/task/noema/scripts"

  echo "== packaging the task"
  cp "$inputs" "$out/task/noema/in/inputs.json"
  cp "$REPO/scripts/encode-reprover-gpu.py" "$REPO/scripts/bootstrap-reprover.py" \
     "$REPO/scripts/benchmark-reprover-device.py" "$out/task/noema/scripts/"
  cp -r "$REPO/src" "$out/task/noema/src"
  find "$out/task/noema/src" -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
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
    --tags Key=Project,Value=noema Key=Purpose,Value=temporary-state-encode >/dev/null
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
        --description "temporary noema encode worker" --vpc-id "$vpc" \
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
      "$REPO/scripts/encode-user-data.sh.in" > "$out/user-data.sh"

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
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$run},{Key=Project,Value=noema},{Key=Purpose,Value=temporary-state-encode}]" \
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
  echo "watch:    scripts/run-encode-aws.sh watch $run"
}

watch_run() {
  local run=$1 out="$REPO/outputs/phase-2-dependency-labels/$1"
  local id; id=$(cat "$out/instance-id")
  echo "instance state : $(aws ec2 describe-instances --region "$REGION" --instance-ids "$id" \
        --query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null || echo gone)"
  echo "console:"
  aws ec2 get-console-output --region "$REGION" --instance-id "$id" --latest \
    --query Output --output text 2>/dev/null \
    | grep -E "(boot|pydeps-done|STAGE|JOB DONE|FINISH|NVIDIA|L40S)" | tail -8
  echo "s3:"
  aws s3 ls "s3://$BUCKET/results/$run/" --region "$REGION" 2>/dev/null || echo "  (not yet)"
}

fetch() {
  local run=$1 out="$REPO/outputs/phase-2-dependency-labels/$1"
  aws s3 cp "s3://$BUCKET/results/$run/result.tar.gz" "$out/result.tar.gz" --region "$REGION"
  tar xzf "$out/result.tar.gz" -C "$out"
  find "$out/noema/out" -type f | sed 's/^/  /'
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
  launch)   launch "${2:?path to inputs.json}" ;;
  watch)    watch_run "${2:?run name}" ;;
  fetch)    fetch "${2:?run name}" ;;
  teardown) teardown "${2:?run name}" ;;
  *) sed -n '2,18p' "$0"; exit 2 ;;
esac
