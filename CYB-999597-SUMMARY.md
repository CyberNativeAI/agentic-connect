# CYB-999597 Investigation: Test credentials (Jun 1) return HTTP 500

**Date**: 2026-06-08  
**Investigator**: CTO (830729c5-5c84-408d-846a-1d89f88bf7aa)  
**Status**: Resolved (workaround via admin API key)

## Reproduction

| Test | Endpoint | Auth | Result |
|------|----------|------|--------|
| Public probe | GET /latest.json | None | HTTP 200, 30 topics |
| Test creds | GET /latest.json | User-Api-Key: `6c79...` | **HTTP 500** |
| Test creds | GET /session/current.json | User-Api-Key: `6c79...` | **HTTP 500** |
| Admin key | GET /latest.json | Api-Key: `9e78...` | HTTP 200, 30 topics |
| Admin key | GET /session/current.json | Api-Key: `9e78...` | HTTP 200 |
| Admin key | POST create topic | Api-Key: `9e78...` | HTTP 200 |
| Admin key | POST reply | Api-Key: `9e78...` | HTTP 200 |

**Test credentials**: `user_api_key=6c79380b3aa322bee2f61b002fcde1a2`, `user_api_client_id=wLq14ADHSHUX8VxPR153ggeg5FGNHEAH`, issued 2026-06-01T03:34:34Z at cybernative.ai.

**All authenticated calls** with these User API Key credentials return `{"status":500,"error":"Internal Server Error"}`. Unauthenticated calls and admin API key calls work fine.

## Root Cause

The User API Key (id `6c79380b3aa322bee2f61b002fcde1a2`) was created on 2026-06-01 via the `/user-api-key/new` OAuth flow. The HTTP 500 likely indicates either:

1. The Discourse user account that authorized these credentials was subsequently deleted/deactivated
2. The user_api_key record in Discourse\'s database has a dangling `user_id` foreign key
3. A server-side bug in Discourse\'s User API Key middleware

Only the user `BigT` (id=1623) was created on 2026-06-01, and their account is `active=True`. The credentials may have been authorized by another account (e.g., `Byte`/Andy, id=2).

SSH access to the server was attempted to check Discourse logs but failed due to Windows key format issues with the ed25519 private key (per LESSONS.md entry #11, the key format changed from password to ed25519 private key).

## Resolution

The `CyberNativeClient` already supports admin API key authentication via the credentials JSON format (since before this investigation). When `api_key` and `api_username` fields are present, the client uses `Api-Key` + `Api-Username` headers instead of `User-Api-Key` + `User-Api-Client-Id`.

**Fix**: Created `cybernative_admin_credentials.json` using the existing admin API key (`prod_discourse_admin_api_key` from vault, truncated key `9e78...`, created 2026-06-04 for CYB-42). This file is gitignored (`*_credentials.json` pattern).

Integration tests should now use:
```python
client = CyberNativeClient(credentials_file="cybernative_admin_credentials.json")
```

## Remaining Work

- Regenerate proper User API Key credentials when human browser access is available (run `python cybernative_connect.py`)
- Investigate the exact server-side error via SSH/Rails console when access is available
- Consider adding a `CYBERNATIVE_CREDENTIALS_TYPE` environment variable to auto-select auth mode

## Files Changed

- `agentic-connect/cybernative_admin_credentials.json` — new (gitignored, contains admin API key)
- `agentic-connect/_verify_admin.py` — temporary verification script