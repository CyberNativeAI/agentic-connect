# Agent Vault (v1) — per-agent secrets manager

Scoped credential store for the local Paperclip runtime. Each agent receives **only** the
secrets it is authorized for; every access is audited; rotation needs no code change.
See **[DESIGN.md](./DESIGN.md)** for the full design and **[ROTATION-RUNBOOK.md](./ROTATION-RUNBOOK.md)**.

## Files
- `vault.mjs` — core (AES-256-GCM crypto, store IO, ACL `authorize()`, audited `getSecret()`).
- `get-secret.mjs` — **runtime helper agents call** to fetch a secret.
- `cli.mjs` — operator admin (`list`, `acl`, `grant`, `set`, `audit`). Never prints values.
- `migrate.mjs` — one-shot CYB-12 → vault migration (already run).
- `skills/cybernative-admin.mjs` — example consumer; reads `cybernative_admin_token` from the vault.

Data (encrypted, instance-level, **never** in git): `…/instances/default/secrets/agent-vault/`.

## Fetch a secret (inside a skill/tool)
```bash
# value is piped straight into the consumer; never echoed
TOKEN_VALUE="$(node get-secret.mjs github_pat)"   # exits 13 + audits if not authorized
```
Identity comes from runtime-set `PAPERCLIP_AGENT_ID` (+ role via `/api/agents/me`).

## Admin
```bash
node cli.mjs list            # keys, ACL, rotation timestamps (no values)
node cli.mjs audit 20        # who/when/which-key/decision (no values)
node cli.mjs grant <key> --role ceo --status active
echo -n | node cli.mjs set <key> < new-value.txt   # set/rotate via STDIN only
```

## Guarantees
- No secret value in source, ACL, logs, audit, or admin stdout — only `get-secret` emits a value, to an authorized caller.
- Every fetch (allow **and** deny) is audited.
- `prod_ssh_root` ships **disabled** (`pending_ceo_approval`) — break-glass not wired until CEO approves.
