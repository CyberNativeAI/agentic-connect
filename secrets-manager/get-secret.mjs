#!/usr/bin/env node
// Runtime secret-fetch helper — THIS is how an agent obtains a credential.
//
//   node get-secret.mjs <key_name>
//
// Caller identity is taken from the runtime-provided PAPERCLIP_AGENT_ID and the
// agent's role (resolved from the Paperclip API /agents/me, cached per call).
// In local_trusted deployment mode these env vars are set by the harness and
// are not agent-forgeable. The helper:
//   1. resolves the caller's agentId + role,
//   2. asks the vault to authorize + decrypt (ACL enforced inside vault.mjs),
//   3. writes an audit record (who/when/which key/decision — never the value),
//   4. prints ONLY the requested secret value to stdout on success.
//
// Pattern for use inside a skill/tool:  the value is captured into a variable
// or piped directly into the consuming command; it is never echoed to logs.

import { getSecret } from './vault.mjs';

async function resolveCaller() {
  const agentId = process.env.PAPERCLIP_AGENT_ID;
  let role = process.env.PAPERCLIP_AGENT_ROLE || null;
  const base = process.env.PAPERCLIP_API_URL || process.env.PAPERCLIP_RUNTIME_API_URL;
  const apiKey = process.env.PAPERCLIP_API_KEY;
  if (!role && base && apiKey) {
    try {
      const r = await fetch(`${base}/api/agents/me`, { headers: { Authorization: `Bearer ${apiKey}` } });
      if (r.ok) { const me = await r.json(); role = me.role; }
    } catch { /* fall through; ACL can still match by agentId */ }
  }
  return { agentId, role };
}

const keyName = process.argv[2];
if (!keyName) { console.error('usage: get-secret.mjs <key_name>'); process.exit(2); }

const caller = await resolveCaller();
if (!caller.agentId) { console.error('PAPERCLIP_AGENT_ID not set; refusing to fetch'); process.exit(3); }

try {
  process.stdout.write(getSecret(keyName, caller)); // value -> stdout only, no newline
} catch (err) {
  console.error(`vault: ${err.message}`); // message names the KEY, never the value
  process.exit(err.code === 'EACCES_VAULT' ? 13 : 1);
}
