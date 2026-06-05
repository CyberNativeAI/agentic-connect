# Per-Agent Secrets Manager — v1 Design (CYB-13)

Owner: CTO · Reviewer: CEO · Parent: CYB-12 · Status: built, **awaiting CEO design review before prod-root wiring**

## 1. Problem
Production credentials were broadcast in plaintext via an issue description (CYB-12),
exposing them to every agent that can read the tracker. We need a store that gives each
agent **only** the credentials it needs, with audit and code-free rotation.

## 2. Mechanism chosen — local encrypted file vault (AES-256-GCM)

| Option | Verdict | Why |
|---|---|---|
| **Encrypted file vault (chosen)** | ✅ | Matches the runtime's existing `local_encrypted`/`master.key` pattern (see `config.json` → `secrets.provider`). Zero new infra/daemon, fully auditable (plain JSON + append-only log), trivial backup, cross-platform Node built-ins only. |
| OS keychain (DPAPI/Keychain) | ➖ | Best at-rest secrecy, but per-OS, awkward for multi-agent ACL + a shared audit trail, harder to back up/inspect. Good as a *future* upgrade for the master key. |
| Full vault (HashiCorp/OpenBao) | ❌ for v1 | Powerful but heavy: a server to run, secure, and patch. Overkill for a single-host local runtime. Bias was "simple + auditable." |

**Decision:** encrypted file vault now; keep an upgrade path to OS-keychain-wrapped master
key and/or OpenBao if the deployment ever leaves a single trusted host.

## 3. Architecture

```
secrets/agent-vault/                 (instance level — OUTSIDE any git repo)
  vault.key   32-byte master key, mode 0600   ← the one thing to protect
  vault.enc   { secrets: { <key>: {iv, ct, tag, createdAt, rotatedAt, meta} } }  AES-256-GCM, per-secret IV
  acl.json    { keys: { <key>: {allowedRoles, allowedAgentIds, status, breakGlass, owner, note} } }
  audit.log   append-only JSONL: {ts, action, key, agentId, role, allowed, reason}  ← never a value

code (this repo / deliverable):
  vault.mjs        core: crypto + store IO + authorize() + audited getSecret()
  get-secret.mjs   runtime helper an agent calls:  node get-secret.mjs <key>
  cli.mjs          operator admin: list / acl / grant / set / audit
  migrate.mjs      one-shot CYB-12 → vault migration (done)
  skills/cybernative-admin.mjs  example consumer that reads cybernative_admin_token from the vault
```

**Security invariants (enforced in code):**
1. Secret values never appear in source, ACL, logs, audit, or stdout of admin tools. Only the
   runtime `get-secret` helper emits a value — to an authorized caller, on stdout, nowhere else.
2. The encrypted store + key live at instance level, never inside a workspace/git repo (`.gitignore` guards it).
3. `getSecret()` audits **every** attempt (allow and deny) with who/when/which-key/decision.
4. `set`/`grant` mutate `vault.enc`/`acl.json` only — **rotation needs no code change.**

## 4. Runtime fetch (scoped injection)
An agent obtains a credential by invoking the helper, which:
1. resolves caller identity from runtime-set `PAPERCLIP_AGENT_ID` (+ role via `/api/agents/me`),
2. calls `vault.authorize(key, agentId, role)` — match by role **or** agent id, and `status === 'active'`,
3. writes an audit record, then
4. on allow, decrypts and prints the value to stdout (piped straight into the consumer); on deny, exits non-zero with a message that names the **key**, never the value.

`local_trusted` deployment (`config.json` → `server.deploymentMode`) means `PAPERCLIP_AGENT_ID`
is harness-set and not agent-forgeable, so identity is trustworthy for v1.

## 5. Key → agent ACL (as seeded)
| Key | Allowed | Status |
|---|---|---|
| `github_pat` | CTO | **active** |
| `cybernative_admin_token` | CEO | **active** — read by the cybernative admin skill from the vault |
| `zoho_smtp` (provider@cybernative.ai) | CEO | **active** |
| `prod_ssh_root` (root@64.176.199.24) | CTO + CEO, break-glass | **DISABLED — `pending_ceo_approval`** |

`prod_ssh_root` is stored but its ACL is **disabled**: any fetch is denied + audited until the CEO
approves. This is the "bring the design to me before wiring broad prod-root access" gate, enforced
in data rather than promised in prose.

## 6. Migration status
All four secrets pulled from CYB-12's description and stored encrypted (see `audit.log` `create`
entries). Integrity fingerprints (SHA-256/12, not reversible): `github_pat 79af609abbb4`,
`cybernative_admin_token 383a3d84f27e`, `prod_ssh_root e7b897d9f7fa`, `zoho_smtp 82d646a0dd66`.

## 7. Board decisions (2026-06-01) & open items
- **Rotation: OFF (final).** Board chose NOT to rotate the four migrated secrets. Vault is built around the existing values as-is. The runbook is retained for future/emergency use only.
- **Redaction: AUTHORIZED.** CEO authorized redacting the 4 plaintext values from CYB-12's description. **Blocked on access:** the API forbids one agent from editing another agent's issue (CYB-12 is CEO-owned) — the issue owner (CEO) or board must apply the ready redaction, or reassign CYB-12 to the CTO to apply it. The exact redacted body (no plaintext) is generated by `redact.mjs` and posted to CYB-13.

Still requiring CEO decision (see request_confirmation on CYB-13):
1. **Approve this v1 design.**
2. **Activate `prod_ssh_root`** break-glass ACL (flip `pending_ceo_approval` → `active`)? Until then it is deny-by-default — "bring the design to me before wiring broad prod-root access."
