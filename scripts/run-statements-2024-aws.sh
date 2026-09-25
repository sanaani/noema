#!/bin/bash
# Print 2024 Mathlib statements for phase 6, on a temporary AWS CPU worker.
#
# results/phase-1-recognition/link-graph-v1/InitialGoals.lean, the printer that
# rendered every corpus statement, prints every theorem in the 2024 graph
# (print-2024/names.txt) from Mathlib f0957a7 with Lean v4.9.0. Importing the
# 4,148 modules needs more memory than a laptop has, so it runs here, on the
# same instance type and prebuilt oleans as phase 2's dependency sweep.
#
# The instance terminates itself (shutdown timer, systemd timer, shutdown-
# terminates). Every resource is tagged for this run and removed by teardown.
#
#   scripts/run-statements-2024-aws.sh launch
#   scripts/run-statements-2024-aws.sh watch    <run-name>
#   scripts/run-statements-2024-aws.sh fetch    <run-name>
#   scripts/run-statements-2024-aws.sh teardown <run-name>
set -euo pipefail

REGION=us-east-2
BUCKET=noema-structural-gpu-159976616274-20260917t220221z
INSTANCE_TYPE=m6i.4xlarge
AMI=ami-00adec9774170bad2                 # Ubuntu 24.04, us-east-2
MATHLIB_REV=f0957a7575317490107578ebaee9efaf8e62a4ab
LEAN_VERSION=v4.9.0
REPO="$(cd "$(dirname "$0")/.." && pwd)"

launch() {
  local run ts
  ts=$(date -u +%Y%m%d-%H%M%S)
  run="noema-stmt2024-$ts"
  local out="$REPO/outputs/phase-6-conjecture-placement/$run"
  mkdir -p "$out"

  echo "== packaging the printer and the draw"
  local P6="$REPO/results/phase-6-conjecture-placement"
  cp "$REPO/results/phase-1-recognition/link-graph-v1/InitialGoals.lean" "$P6/print-2024/"
  tar czf "$out/task.tar.gz" -C "$P6" print-2024/InitialGoals.lean print-2024/names.txt print-2024/modules.txt
  rm "$P6/print-2024/InitialGoals.lean"
  aws s3 cp "$out/task.tar.gz" "s3://$BUCKET/$run-task.tar.gz" --region "$REGION"

  echo "== IAM role, scoped to this run's two keys"
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
    --tags Key=Project,Value=noema Key=Purpose,Value=temporary-statement-print >/dev/null
  aws iam put-role-policy --role-name "$run" --policy-name s3-temp \
    --policy-document "file://$out/policy.json"
  # Session Manager, so a stuck run can be inspected without SSH and without an
  # ingress rule. A sweep that goes quiet is otherwise undiagnosable from
  # outside: console output, CPU and EBS metrics cannot separate "still
  # importing Mathlib" from "hung", and attaching this to a live run is too
  # late -- the agent has already backed off by the time you want it.
  aws iam attach-role-policy --role-name "$run" \
    --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
  aws iam create-instance-profile --instance-profile-name "$run" >/dev/null
  aws iam add-role-to-instance-profile --instance-profile-name "$run" --role-name "$run"

  echo "== security group, egress only"
  local vpc sg subnet
  vpc=$(aws ec2 describe-vpcs --region "$REGION" --filters Name=isDefault,Values=true \
        --query 'Vpcs[0].VpcId' --output text)
  sg=$(aws ec2 create-security-group --region "$REGION" --group-name "$run" \
        --description "temporary noema statement worker" --vpc-id "$vpc" \
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
      -e "s|@MATHLIB_REV@|$MATHLIB_REV|g" -e "s|@LEAN_VERSION@|$LEAN_VERSION|g" \
      "$REPO/scripts/statements-2024-user-data.sh.in" > "$out/user-data.sh"

  echo "== waiting for the instance profile to propagate"
  sleep 20

  local id
  id=$(aws ec2 run-instances --region "$REGION" \
    --image-id "$AMI" --instance-type "$INSTANCE_TYPE" --count 1 \
    --iam-instance-profile "Name=$run" \
    --instance-initiated-shutdown-behavior terminate \
    --metadata-options 'HttpTokens=required,HttpEndpoint=enabled,HttpPutResponseHopLimit=1' \
    --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":150,"VolumeType":"gp3","Encrypted":true,"DeleteOnTermination":true}}]' \
    --network-interfaces "[{\"DeviceIndex\":0,\"SubnetId\":\"$subnet\",\"Groups\":[\"$sg\"],\"AssociatePublicIpAddress\":true,\"DeleteOnTermination\":true}]" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$run},{Key=Project,Value=noema},{Key=Purpose,Value=temporary-statement-print}]" \
    --user-data "file://$out/user-data.sh" \
    --query 'Instances[0].InstanceId' --output text)
  echo "$id" > "$out/instance-id"
  echo "$sg"  > "$out/security-group-id"
  echo
  echo "run       $run"
  echo "instance  $id  ($INSTANCE_TYPE, self-terminating)"
  echo "artifacts $out"
  echo
  echo "watch:    scripts/run-statements-2024-aws.sh watch $run"
}

watch_run() {
  local run=$1 out="$REPO/outputs/phase-6-conjecture-placement/$1"
  local id; id=$(cat "$out/instance-id")
  echo "instance state : $(aws ec2 describe-instances --region "$REGION" --instance-ids "$id" \
        --query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null || echo gone)"
  echo "console progress :"; aws ec2 get-console-output --region "$REGION" --instance-id "$id" --latest --query Output --output text 2>/dev/null | grep -E "(ALIVE|oleans|STAGE|PROGRESS|DONE|FINISH|error)" | tail -6
  echo "result in s3   :"
  aws s3 ls "s3://$BUCKET/results/$run/" --region "$REGION" 2>/dev/null || echo "  (not yet)"
}

shell_run() {
  local run=$1 out="$REPO/outputs/phase-6-conjecture-placement/$1"
  local id; id=$(cat "$out/instance-id")
  local ping
  ping=$(aws ssm describe-instance-information --region "$REGION" \
    --filters "Key=InstanceIds,Values=$id" \
    --query 'InstanceInformationList[0].PingStatus' --output text 2>/dev/null)
  if [ "$ping" != "Online" ]; then
    echo "instance $id is not registered with SSM (ping=${ping:-none})."
    echo "it registers a few minutes after boot; until then use 'watch'."
    return 1
  fi
  aws ssm start-session --region "$REGION" --target "$id"
}

fetch() {
  local run=$1 out="$REPO/outputs/phase-6-conjecture-placement/$1"
  aws s3 cp "s3://$BUCKET/results/$run/result.tar.gz" "$out/result.tar.gz" --region "$REGION"
  tar xzf "$out/result.tar.gz" -C "$out"
  find "$out/noema/out" -type f | sed 's/^/  /'
}

teardown() {
  local run=$1 out="$REPO/outputs/phase-6-conjecture-placement/$1"
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
  # Managed policies must be detached before the role can be deleted.
  aws iam detach-role-policy --role-name "$run" \
    --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore || true
  aws iam delete-role --role-name "$run" || true
  aws s3 rm "s3://$BUCKET/$run-task.tar.gz" --region "$REGION" || true
  echo "torn down: $run"
}

case "${1:-}" in
  launch)   launch ;;
  watch)    watch_run "${2:?run name}" ;;
  shell)    shell_run "${2:?run name}" ;;
  fetch)    fetch "${2:?run name}" ;;
  teardown) teardown "${2:?run name}" ;;
  *) sed -n '2,24p' "$0"; exit 2 ;;
esac
