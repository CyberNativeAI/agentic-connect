#!/usr/bin/env node
// Redact the four plaintext secrets from CYB-12's description, replacing each
// value with a vault key-name reference. Authorized by CEO (board decision,
// 2026-06-01). Values are matched and removed in-memory; never printed/logged.
// Idempotent: re-running after redaction is a no-op.
//
//   node redact.mjs            (dry-run: print the SAFE redacted body)
//   node redact.mjs --commit   (PATCH CYB-12 description)

const COMMIT = process.argv.includes('--commit');
const CYB12_ID = 'dd7833f5-ce17-4b7c-90b5-f7e577abe91b';
const base = process.env.PAPERCLIP_API_URL || process.env.PAPERCLIP_RUNTIME_API_URL;
const apiKey = process.env.PAPERCLIP_API_KEY;

const REF = (key) => `\`‹secret moved to agent-vault — key: ${key} (see CYB-13); not rotated per board decision›\``;

// Ordered replacements. Each removes ONLY the secret value, preserving
// surrounding context (labels, IP, email, "(zoho)") so the issue stays readable.
const RULES = [
  // GitHub PAT: the whole token run starting at the public "github_pat" prefix
  // (markdown-escaped as github\_pat\_...). Tolerate optional backslashes.
  { key: 'github_pat', re: /github\\?_pat\\?_[\\A-Za-z0-9_]+/g },
  // 64-hex cybernative admin token (keep the "admin token for you:" lead-in).
  { key: 'cybernative_admin_token', re: /(admin token for you:\s*\n\s*)[0-9a-fA-F]{64}/g, keepGroup: true },
  // prod ssh root password (keep "64.176.199.24 root ").
  { key: 'prod_ssh_root', re: /(64\.176\.199\.24\s+root\s+)(?!`)\S+/g, keepGroup: true },
  // zoho password (keep the mailto and " (zoho)").
  { key: 'zoho_smtp', re: /(mailto:provider@cybernative\.ai\)\s+)\S+(\s+\(zoho\))/g, keepGroup: true, trailGroup: true },
];

function redact(md) {
  let out = md;
  const hits = {};
  for (const rule of RULES) {
    out = out.replace(rule.re, (m, g1, g2) => {
      hits[rule.key] = (hits[rule.key] || 0) + 1;
      if (rule.trailGroup) return `${g1}${REF(rule.key)}${g2}`;
      if (rule.keepGroup) return `${g1}${REF(rule.key)}`;
      return REF(rule.key);
    });
  }
  return { out, hits };
}

async function main() {
  if (!base || !apiKey) { console.error('missing API env'); process.exit(1); }
  const r = await fetch(`${base}/api/issues/${CYB12_ID}`, { headers: { Authorization: `Bearer ${apiKey}` } });
  if (!r.ok) { console.error(`fetch failed: ${r.status}`); process.exit(1); }
  const md = (await r.json()).description || '';
  const { out, hits } = redact(md);

  console.log(`redactions: ${JSON.stringify(hits)}`);
  console.log(`length ${md.length} -> ${out.length}`);
  console.log('--- SAFE redacted body (values removed) ---');
  console.log(out);

  if (!COMMIT) { console.log('--- dry-run; re-run with --commit to PATCH ---'); return; }

  const headers = { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' };
  if (process.env.PAPERCLIP_RUN_ID) headers['X-Paperclip-Run-Id'] = process.env.PAPERCLIP_RUN_ID;
  const pr = await fetch(`${base}/api/issues/${CYB12_ID}`, {
    method: 'PATCH',
    headers,
    body: JSON.stringify({ description: out }),
  });
  const body = await pr.text();
  console.log(`PATCH status ${pr.status}: ${body.slice(0, 300)}`);
}

main().catch((e) => { console.error(e.message); process.exit(1); });
