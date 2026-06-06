#!/usr/bin/env bash
# CYB-175 — Migrate CyberNative.ai creds to Paperclip secrets.
#
# Secret creation is board-gated, so this MUST be run by the human board user.
# One-time auth, then run this script:
#
#   paperclipai auth login          # authenticate the CLI as the board user
#   bash migrate_creds_to_secrets.sh
#
# Values are read from the gitignored credentials JSON and passed via env
# (--value-env), so the secret values never appear on the command line,
# in shell history, or in any ticket/log.
set -euo pipefail

COMPANY_ID="${PAPERCLIP_COMPANY_ID:-ae94aa07-dea0-4cbe-b7f1-ddefd87c0122}"
CRED_FILE="$(dirname "$0")/cybernative_agent_credentials.json"

if [[ ! -f "$CRED_FILE" ]]; then
  echo "ERROR: $CRED_FILE not found." >&2
  exit 1
fi

# Pick a working Python (Windows often aliases bare `python` to a store stub).
PY=""
for cand in python3 py python; do
  if "$cand" -c "import sys" >/dev/null 2>&1; then PY="$cand"; break; fi
done
if [[ -z "$PY" ]]; then
  echo "ERROR: no working Python found (tried python3, py, python)." >&2
  exit 1
fi

# Extract the two sensitive values from the JSON without echoing them.
CYBERNATIVE_USER_API_KEY="$("$PY" -c "import json,sys;print(json.load(open(sys.argv[1]))['user_api_key'])" "$CRED_FILE")"
CYBERNATIVE_USER_API_CLIENT_ID="$("$PY" -c "import json,sys;print(json.load(open(sys.argv[1]))['user_api_client_id'])" "$CRED_FILE")"
export CYBERNATIVE_USER_API_KEY CYBERNATIVE_USER_API_CLIENT_ID

echo "Creating secret: CYBERNATIVE_USER_API_KEY"
paperclipai secrets create \
  --company-id "$COMPANY_ID" \
  --name "CyberNative User API Key" \
  --key "CYBERNATIVE_USER_API_KEY" \
  --value-env "CYBERNATIVE_USER_API_KEY" \
  --description "CyberNative.ai user_api_key for the agentic-connect connector (issue CYB-14). User BigT (id 1623), scopes read,write,notifications,session_info."

echo "Creating secret: CYBERNATIVE_USER_API_CLIENT_ID"
paperclipai secrets create \
  --company-id "$COMPANY_ID" \
  --name "CyberNative User API Client ID" \
  --key "CYBERNATIVE_USER_API_CLIENT_ID" \
  --value-env "CYBERNATIVE_USER_API_CLIENT_ID" \
  --description "CyberNative.ai user_api_client_id paired with CYBERNATIVE_USER_API_KEY (issue CYB-14)."

echo
echo "Done. Verify with: paperclipai secrets list --company-id $COMPANY_ID"
echo "After confirming the secrets exist, you may delete the plaintext file:"
echo "  $CRED_FILE"
