#!/usr/bin/env bash
# deploy-well-known.sh — Deploy .well-known/mcp.json to cybernative.ai
# Requires SSH key-based access or sshpass for password auth.
# Run from agentic-connect repo root.

set -euo pipefail

SSH_HOST="root@64.176.199.24"
REMOTE_WELL_KNOWN="/var/www/discourse/public/.well-known"
LOCAL_FILE=".well-known/mcp.json"

echo "Deploying .well-known/mcp.json to cybernative.ai..."

if command -v sshpass &>/dev/null && [ -n "${SSHPASS:-}" ]; then
  sshpass -e scp -o StrictHostKeyChecking=no "$LOCAL_FILE" "$SSH_HOST:$REMOTE_WELL_KNOWN/"
elif [ -n "${SSHPASS:-}" ]; then
  echo "sshpass not found; falling back to interactive SCP" >&2
  scp -o StrictHostKeyChecking=no "$LOCAL_FILE" "$SSH_HOST:$REMOTE_WELL_KNOWN/"
else
  scp -o StrictHostKeyChecking=no "$LOCAL_FILE" "$SSH_HOST:$REMOTE_WELL_KNOWN/"
fi

echo "Deployed. Verify: curl -s https://cybernative.ai/.well-known/mcp.json | head -c 200"
