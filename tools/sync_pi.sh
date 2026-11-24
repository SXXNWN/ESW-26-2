#!/bin/sh
set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

exec rsync -az \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude '.runtime/' \
  --exclude 'artifacts/' \
  --exclude '__pycache__/' \
  --exclude '.pytest_cache/' \
  -e "ssh -i $project_root/.runtime/pi_test_ed25519 -o BatchMode=yes -o ConnectTimeout=10 -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$project_root/.runtime/pi_known_hosts" \
  "$project_root/" \
  shinsangwon@192.168.100.2:/home/shinsangwon/Santas_Delivery/
