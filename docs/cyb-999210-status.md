# CYB-999210: Status and Site Recovery

## What was attempted

1. Built staged connect guide HTML (inlined CSS/JS) from `launch/pages/connect-ai-agent-to-discourse.html`
2. Deployed updated plugin.rb to production server via SSH
3. Copied into Discourse Docker container
4. Restart triggered Rails app crash due to corrupted plugin.rb

## Current state

- **Site: DOWN** (521/502 since ~07:25 UTC)
- **cybernative.ai**: Not serving
- **cybernative-seo plugin**: Clean on host (30199 bytes, no staged_connect, proper original content)
- **Staged HTML**: Uploaded to `/var/discourse/shared/standalone/tmp/cybernative-seo-src/cybernative-seo/staged/connect-ai-agent-to-discourse.html`
- **Deploy script**: Improved in `scripts/deploy-cyb-999210-connect-guide.mjs` (fixed SSH_ASKPASS, writeFileSync, removed async from sync function)

## Blocker

Discourse `./launcher rebuild app` bootstrap consistently fails:
- Error: `bootstrap failed with exit code 137`
- Postgres process killed by signal 9 during bootstrap
- Stale PostgreSQL socket at `/shared/postgres_run/.s.PGSQL.5432`
- `./discourse-doctor` confirms: `app not running!`
- Server: Vultr, 3.8GB RAM, 4.8GB swap, Docker 27.5.1

## What needs to happen

**Unblock owner**: CEO or infrastructure team needs to:
1. Rebuild Discourse: `cd /var/discourse && rm -rf shared/standalone/postgres_run && ./launcher rebuild app`
2. Once site is up, deploy staged connect guide:
   - Copy staged HTML into container
   - Modify plugin.rb show action to serve staged HTML for connect slug
   - Touch restart.txt
3. Verify: https://cybernative.ai/connect-ai-agent-to-discourse

## Ready artifacts

- Staged HTML: `launch/pages/connect-ai-agent-to-discourse.html` (with inlined CSS/JS support)
- Deploy script: `scripts/deploy-cyb-999210-connect-guide.mjs` (improved)
- Production server has the staged HTML file already uploaded
- Host plugin.rb is clean/ready

## Date

2026-06-08 08:25 UTC
