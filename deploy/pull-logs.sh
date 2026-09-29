#!/usr/bin/env bash
# Run on YOUR LAPTOP. Copies the last N minutes of API logs from the VM into
# ~/claimshub-logs, the folder Splunk watches. Schedule it with cron every 5 minutes:
#   */5 * * * * /path/to/ClaimsHub/deploy/pull-logs.sh >> /tmp/pull-logs.out 2>&1
set -euo pipefail
VM="${CLAIMSHUB_VM:?set CLAIMSHUB_VM=ubuntu@<vm-public-ip>}"
MINUTES="${1:-5}"
OUT_DIR="$HOME/claimshub-logs"
mkdir -p "$OUT_DIR"
ssh -o BatchMode=yes "$VM" \
  "docker logs --since ${MINUTES}m \$(docker ps -qf name=api) 2>&1 | grep '^{'" \
  >> "$OUT_DIR/api-$(date +%Y%m%d).log" || true
