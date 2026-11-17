#!/bin/sh
set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

exec ssh \
  -i "$project_root/.runtime/pi_test_ed25519" \
  -o IdentitiesOnly=yes \
  -o BatchMode=yes \
  -o StrictHostKeyChecking=yes \
  -o UserKnownHostsFile="$project_root/.runtime/pi_known_hosts" \
  shinsangwon@192.168.100.2 "$@"
