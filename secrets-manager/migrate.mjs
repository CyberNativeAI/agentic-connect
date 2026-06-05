#!/usr/bin/env node
// One-shot migration: pull the four production secrets that were pasted in
// plaintext into CYB-12's description, store them ENCRYPTED in the vault, and
// seed the ACL. The plaintext values are read from the API, held only as local
// buffers, and written through the vault's encrypt path. They are NEVER printed
// or logged — the script emits key name, byte length, and a SHA-256 fingerprint
// (a one-way digest) purely so a human can confirm integrity / later confirm a
// rotation actually changed the value.
//
// Usage:  node migrate.mjs            (dry-run: parse + fingerprint, no write)
//         node migrate.mjs --commit   (write to vault + seed ACL)

import { createHash } from 'node:crypto';
import { putSecret, loadAcl, saveAcl } from './vault.mjs';

const COMMIT = process.argv.includes('--commit');

const CYB12_ID = 'dd7833f5-ce17-4b7c-90b5-f7e577abe91b';
const CTO_ID = '830729c5-5c84-408d-846a-1d89f88bf7aa';
const CEO_ID = '9c6d88ab-3135-4221-afba-bc7c29616fd4';

const base = process.env.PAPERCLIP_API_URL || process.env.PAPERCLIP_RUNTIME_API_URL;
const apiKey = process.env.PAPERCLIP_API_KEY;

// Undo markdown backslash-escaping: "\_" -> "_", "\[" -> "[", "\*" -> "*", etc.
const unescapeMd = (s) => s.replace(/\\(.)/g, '$1');
const fp = (v) => createHash('sha256').update(v, 'utf8').digest('hex').slice(0, 12);

// Each extractor returns the cleartext secret value (string) from the raw md.
const EXTRACTORS = {
  github_pat: (md) => {
    const m = md.match(/github[\\A-Za-z0-9_]+/);
    return m ? unescapeMd(m[0]) : null;
  },
  cybernative_admin_token: (md) => {
    // 64-hex global admin token that follows the "admin token for you:" line.
    const m = md.match(/admin token for you:\s*\n\s*([0-9a-fA-F]{64})/);
    return m ? m[1] : null;
  },
  prod_ssh_root: (md) => {
    const m = md.match(/64\.176\.199\.24\s+root\s+(\S+)/);
    return m ? unescapeMd(m[1]) : null;
  },
  zoho_smtp: (md) => {
    const m = md.match(/mailto:provider@cybernative\.ai\)\s+(\S+)\s+\(zoho\)/);
    return m ? unescapeMd(m[1]) : null;
  },
};

// ACL seed. prod_ssh_root is intentionally LEFT DISABLED (pending_ceo_approval)
// so the break-glass path is not wired until the CEO reviews the design.
const ACL_SEED = {
  github_pat:              { allowedRoles: ['cto'],        allowedAgentIds: [CTO_ID],          status: 'active',               breakGlass: false, owner: 'CTO',       note: 'GitHub PAT — CTO only' },
  cybernative_admin_token: { allowedRoles: ['ceo'],        allowedAgentIds: [CEO_ID],          status: 'active',               breakGlass: false, owner: 'CEO',       note: 'cybernative.ai global admin — read by the admin skill from the vault' },
  zoho_smtp:               { allowedRoles: ['ceo'],        allowedAgentIds: [CEO_ID],          status: 'active',               breakGlass: false, owner: 'CEO',       note: 'provider@cybernative.ai Zoho SMTP' },
  prod_ssh_root:           { allowedRoles: ['cto', 'ceo'], allowedAgentIds: [CTO_ID, CEO_ID],  status: 'pending_ceo_approval', breakGlass: true,  owner: 'CTO+CEO',   note: 'prod root @64.176.199.24 — break-glass, DISABLED until CEO approves' },
};

async function main() {
  if (!base || !apiKey) { console.error('missing PAPERCLIP_API_URL / PAPERCLIP_API_KEY'); process.exit(1); }
  const r = await fetch(`${base}/api/issues/${CYB12_ID}`, { headers: { Authorization: `Bearer ${apiKey}` } });
  if (!r.ok) { console.error(`fetch CYB-12 failed: ${r.status}`); process.exit(1); }
  const md = (await r.json()).description || '';

  const report = [];
  const values = {}; // keyName -> cleartext, local only, never printed
  for (const [key, fn] of Object.entries(EXTRACTORS)) {
    const v = fn(md);
    if (!v) { report.push({ key, found: false }); continue; }
    values[key] = v;
    report.push({ key, found: true, bytes: Buffer.byteLength(v, 'utf8'), sha256_12: fp(v) });
  }

  console.log(`mode: ${COMMIT ? 'COMMIT' : 'dry-run'}`);
  console.log(JSON.stringify(report, null, 2)); // fingerprints only, no values

  const missing = report.filter((x) => !x.found).map((x) => x.key);
  if (missing.length) { console.error(`could not extract: ${missing.join(', ')} — aborting`); process.exit(2); }

  if (!COMMIT) { console.log('dry-run only; re-run with --commit to write'); return; }

  for (const key of Object.keys(values)) {
    const meta = putSecret(key, () => values[key], { by: 'migrate.mjs (CYB-13)', source: 'CYB-12 description', owner: ACL_SEED[key].owner });
    console.log(`stored ${key} (created ${meta.createdAt}${meta.existed ? ', ROTATED' : ''})`);
  }
  const acl = loadAcl();
  for (const [key, e] of Object.entries(ACL_SEED)) acl.keys[key] = { ...e };
  saveAcl(acl);
  console.log('ACL seeded. prod_ssh_root left DISABLED (pending_ceo_approval).');
}

main().catch((e) => { console.error(e.message); process.exit(1); });
