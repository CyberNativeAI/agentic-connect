# CYB-999597 Investigation Report

**Date**: 2026-06-08  
**Investigators**: CTO (830729c5-5c84-408d-846a-1d89f88bf7aa), CommunityEngineer (CYB-999620)  
**Status**: RESOLVED — root cause identified

## Problem

Test User API Key credentials issued 2026-06-01 (`user_api_key=6c79...`, `client_id=wLq14...`) returned HTTP 500 on all authenticated Discourse API calls (`/latest.json`, `/session/current.json`).

## Root Cause

**The `User-Api-Client-Id` header triggers a Cloudflare WAF block** on the cybernative.ai Cloudflare-proxied Discourse server. The header is not required by Discourse for authentication — `User-Api-Key` alone suffices.

The 500 response includes no useful error detail (`{"status":500,"error":"Internal Server Error"}`) and returns in ~15ms (too fast for a real server error), consistent with a WAF edge response.

Discovered by CommunityEngineer in CYB-999620. Verified here:

| Test | Headers | Result |
|------|---------|--------|
| Test creds | `User-Api-Key` + `User-Api-Client-Id` | HTTP 500 (WAF block) |
| Test creds | `User-Api-Key` ONLY | HTTP 200 — works |
| Admin API key | `Api-Key` + `Api-Username` | HTTP 200 — works (different header names, not affected) |

## Who owns these credentials?

The authenticated user is **BigT** (id=1623, created 2026-06-01), confirmed via `GET /session/current.json` with `User-Api-Key` (no client-id).

## Resolution

1. **Immediate**: Remove `User-Api-Client-Id` header from all authenticated requests. Discourse accepts `User-Api-Key` alone. This was done in CYB-999620 (upstream commit `2a51fd4`).
2. **Fallback**: The admin API key works as a drop-in replacement for all operations (read, write, create, reply) using `Api-Key` + `Api-Username` headers. Credentials file at `cybernative_admin_credentials.json` (gitignored).
3. **Code**: `CyberNativeClient` already supports admin API key auth via `api_key`/`api_username` fields in credentials JSON.
4. **Documentation**: LESSONS.md entry added for both CYB-999620 (Cloudflare WAF + client-id) and CYB-999597 (admin key fallback).

## Lessons

1. **Cloudflare WAF can silently block specific HTTP headers** — always test with minimal headers when debugging auth 500s.
2. **Discourse User API Key auth doesn't require `User-Api-Client-Id`** — the key alone is sufficient.
3. **Admin API keys bypass WAF header rules** — maintain one as a fallback for integration tests.
4. **~15ms response time on a 500 = edge proxy/WAF, not application server error.**

## Artifacts

- `agentic-connect/CYB-999597-SUMMARY.md` — this report
- `agentic-connect/LESSONS.md` — updated with both lessons
- `agentic-connect/cybernative_admin_credentials.json` — gitignored admin credentials