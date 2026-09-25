#!/bin/bash
# A Lean checker for phase 6's theorem-writing pilot, on a temporary AWS CPU worker.
#
# Mathlib 09712d48 with Lean v4.35.0-rc2 and its prebuilt oleans, as phase 5
# printed from; `import Mathlib` needs more memory than the laptop has. The
# worker installs /opt/check.sh and waits; scripts/pilot-check.py sends it
# candidate files over SSM Run Command and reads back Lean's output.
#
# The instance terminates itself after 8 hours (shutdown timer, systemd timer,
# shutdown-terminates). Every resource is tagged for this run and removed by
# teardown.
#
#   scripts/run-lean-check-aws.sh launch
#   scripts/run-lean-check-aws.sh watch    <run-name>
#   scripts/run-lean-check-aws.sh teardown <run-name>
set -euo pipefail

REGION=us-east-2
BUCKET=noema-structural-gpu-159976616274-20260917t220221z
INSTANCE_TYPE=m6i.4xlarge
AMI=ami-00adec9774170bad2                 # Ubuntu 24.04, us-east-2
MATHLIB_REV=09712d488fdbecc0b1d9248a283cf2aa31081b55
LEAN_VERSION=v4.35.0-rc2
REPO="$(cd "$(dirname "$0")/.." && pwd)"

launch() {
  local run ts
  ts=$(date -u +%Y%m%d-%H%M%S)
  run="noema-leancheck-$ts"
  local out="$REPO/outputs/phase-6-conjecture-placement/$run"
  mkdir -p "$out"

  echo "== IAM role, scoped to this run's two keys"
  cat > "$out/trust.json" <<'JSON'
{"Version":"2012-10-17","Statement":[{"Effect":"Allow",
 "Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}
JSON
  cat > "$out/policy.json" <<JSON
{"Version":"2012-10-17","Statement":[
 {"Effect":"Allow","Action":["s3:PutObject"],
  "Resource":["arn:aws:s3:::$BUCKET/results/$run/*"]}]}
JSON
  aws iam create-role --role-name "$run" \
    --assume-role-policy-document "file://$out/trust.json" \
    --tags Key=Project,Value=noema Key=Purpose,Value=temporary-lean-check >/dev/null
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
        --description "temporary noema lean checker" --vpc-id "$vpc" \
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
      "$REPO/scripts/lean-check-user-data.sh.in" > "$out/user-data.sh"

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
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$run},{Key=Project,Value=noema},{Key=Purpose,Value=temporary-lean-check}]" \
    --user-data "file://$out/user-data.sh" \
    --query 'Instances[0].InstanceId' --output text)
  echo "$id" > "$out/instance-id"
  echo "$sg"  > "$out/security-group-id"
  echo
  echo "run       $run"
  echo "instance  $id  ($INSTANCE_TYPE, self-terminating)"
  echo "artifacts $out"
  echo
  echo "watch:    scripts/run-lean-check-aws.sh watch $run"
}

watch_run() {
  local run=$1 out="$REPO/outputs/phase-6-conjecture-placement/$1"
  local id; id=$(cat "$out/instance-id")
  echo "instance state : $(aws ec2 describe-instances --region "$REGION" --instance-ids "$id" \
        --query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null || echo gone)"
  echo "console progress :"; aws ec2 get-console-output --region "$REGION" --instance-id "$id" --latest --query Output --output text 2>/dev/null | grep -E "(ALIVE|oleans|STAGE|READY|FINISH|error)" | tail -6
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
  echo "torn down: $run"
}

case "${1:-}" in
  launch)   launch ;;
  watch)    watch_run "${2:?run name}" ;;
  shell)    shell_run "${2:?run name}" ;;
  teardown) teardown "${2:?run name}" ;;
  *) sed -n '2,15p' "$0"; exit 2 ;;
esac
