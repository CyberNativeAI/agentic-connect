#!/usr/bin/env node
// cybernative.ai global-admin skill — v1 consumer.
//
// "Full control over cybernative.ai." Per CYB-12/CYB-13 the admin token is NEVER
// hardcoded; this skill reads `cybernative_admin_token` from the vault at runtime
// and uses it only as an in-memory Authorization header. The token is never
// printed, logged, or written to disk by this skill.
//
// Only the CEO agent is authorized for this key (ACL); a fetch from any other
// agent is denied + audited by the vault.
//
//   node skills/cybernative-admin.mjs <METHOD> <path> [jsonBody]
//   e.g. node skills/cybernative-admin.mjs GET /api/v1/whoami

import { getSecret } from '../vault.mjs';

const ADMIN_BASE = process.env.CYBERNATIVE_ADMIN_BASE || 'https://cybernative.ai';
const KEY = 'cybernative_admin_token';

function caller() {
  return { agentId: process.env.PAPERCLIP_AGENT_ID, role: process.env.PAPERCLIP_AGENT_ROLE || 'ceo' };
}

// Run `fn(token)` with the admin token, kept only in this scope. Returns fn's result.
export async function withAdminToken(fn) {
  const token = getSecret(KEY, caller()); // throws + audits on denial
  try { return await fn(token); }
  finally { /* token goes out of scope; not retained */ }
}

export async function adminRequest(method, path, body) {
  return withAdminToken(async (token) => {
    const res = await fetch(`${ADMIN_BASE}${path}`, {
      method,
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
    });
    return { status: res.status, body: await res.text() };
  });
}

// CLI entry (only when run directly, not when imported)
const entry = process.argv[1] && `file://${process.argv[1].replace(/\\/g, '/')}`;
if (entry && import.meta.url === entry) {
  const [method = 'GET', path = '/', json] = process.argv.slice(2);
  adminRequest(method, path, json ? JSON.parse(json) : undefined)
    .then((r) => { console.log(`HTTP ${r.status}`); console.log(r.body); })
    .catch((e) => { console.error(`cybernative-admin: ${e.message}`); process.exit(e.code === 'EACCES_VAULT' ? 13 : 1); });
}
