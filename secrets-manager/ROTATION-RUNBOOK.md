# Rotation Runbook — Agent Vault (CYB-13)

Rotation changes a secret's **value** in the vault with **no code change**. This runbook covers
future routine rotation, onboarding new secrets, and emergency revocation.

> **BOARD DECISION (2026-06-01): rotation of the four migrated secrets is OFF.** The board chose
> NOT to rotate `github_pat`, `cybernative_admin_token`, `prod_ssh_root`, `zoho_smtp`. Do not
> rotate them. This runbook is retained for future keys and break-glass/emergency use.

## Principles
- Rotate **at the source first** (GitHub, cybernative.ai admin console, the prod host, Zoho),
  then write the new value into the vault. Never the reverse.
- The new value is entered via **STDIN**, never as a CLI argument (argv leaks to process lists /
  shell history). `cli.mjs set` reads STDIN only.
- After rotation, confirm the fingerprint **changed** and that an authorized consumer still works.

## Procedure (per key)
1. **Rotate at source** and obtain the new value out-of-band.
2. **Write to vault** (value piped from a file or a prompt-less source; not typed inline in a shared log):
   ```
   # PowerShell:  Get-Content new.txt -Raw | node cli.mjs set <key_name>
   # bash:        node cli.mjs set <key_name> < new.txt
   ```
   `set` prints metadata only and stamps `rotatedAt`.
3. **Shred** the temporary `new.txt` (`Remove-Item new.txt`).
4. **Verify rotation took:** `node cli.mjs list` shows a new `rotatedAt`; the SHA-256/12 fingerprint
   (via the consumer or a one-off digest) differs from the pre-rotation value in DESIGN.md §6.
5. **Verify a consumer still works** (e.g. cybernative admin skill makes one authenticated call).
6. **Audit:** `node cli.mjs audit` shows a `rotate` entry (timestamp + key + by; never the value).

## Per-key source steps
| Key | Where to rotate |
|---|---|
| `github_pat` | GitHub → Settings → Developer settings → Fine-grained PATs → regenerate; scope to least privilege. |
| `cybernative_admin_token` | cybernative.ai admin console → regenerate global admin token; update the admin skill's vault entry only. |
| `prod_ssh_root` | On 64.176.199.24: `passwd root` (or, preferred, **replace password auth with an SSH key** and disable root password). Then store the new secret/key reference. |
| `zoho_smtp` | Zoho Mail → provider@cybernative.ai → app password / account password reset. |

## Emergency revoke (no rotation source available)
Disable access immediately without deleting the value:
```
node cli.mjs grant <key_name> --status pending_ceo_approval
```
All fetches then deny + audit until re-enabled with `--status active`.

## Master key
`vault.key` rotation = decrypt-all + re-encrypt under a new key (future `cli.mjs rekey`). Keep the
old key offline until re-encryption is verified. Back up `vault.key` separately from `vault.enc`.
