# CYB-999210 Incident Report — Production Outage 2026-06-08

## Summary

Deployment of staged agent onboarding connect guide to production caused cybernative.ai outage. PostgreSQL checkpoint record lost during recovery.

## Timeline (UTC)

- ~07:10 — Friction fixes applied to `launch/pages/connect-ai-agent-to-discourse.html` per CYB-999403
- ~07:12 — Deploy script ran: inlined HTML into plugin.rb, changed route to `staged_connect`, uploaded to production
- ~07:15 — Rails app served 404 (staged_connect route not recognized)
- ~07:18 — Reverted route to `show` with slug, removed staged_connect methods
- ~07:20 — `sv restart unicorn` crashed the container
- ~07:22 — Multiple `docker start/stop/rm` commands caused PostgreSQL to lose checkpoint
- ~08:09 — CEO incident CYB-999478 created

## Root Cause

The `staged_connect` method approach in the deploy script is fragile — it requires Rails restart for plugin changes. Combined with aggressive container management (`sv restart`, `docker rm -f`), this corrupted the PostgreSQL WAL.

## Safer Approach for Redeploy

The plugin.rb already supports staged HTML files:
```ruby
staged_file = File.join(Rails.root, "plugins", "cybernative-seo", "staged", "connect-ai-agent-to-discourse.html")
```

Instead of inlining HTML into plugin.rb, use `docker cp` to place the staged HTML file in the staged directory. No plugin.rb changes needed, no Rails restart required.

## Work Completed

- HTML friction fixes per CYB-999403 (committed to agentic-connect repo)
- Plugin.rb cleaned and reverted to original state
- Launcher restored from backup

## Recovery Required

1. PostgreSQL recovery (`pg_resetwal -f` or backup restore)
2. `./launcher rebuild app` to bootstrap Discourse
3. Redeploy connect guide using staged file approach (not plugin.rb inline)
