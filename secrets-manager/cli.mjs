#!/usr/bin/env node
// Vault admin CLI. Operator-facing. Never prints a secret value.
//
// Usage:
//   node cli.mjs list                       # keys + ACL + rotation timestamps
//   node cli.mjs audit [N]                  # tail last N audit lines (no values)
//   node cli.mjs acl                        # show ACL
//   node cli.mjs grant <key> --role r --id id --status active|pending_ceo_approval [--break-glass]
//   node cli.mjs set <key>                  # set/rotate; reads value from STDIN (never argv)
//   node cli.mjs status                     # vault location + counts
//
// `set` reads the value from STDIN so it never lands in shell history or argv.

import { readFileSync } from 'node:fs';
import { listKeys, loadAcl, saveAcl, putSecret, paths } from './vault.mjs';

const [cmd, ...rest] = process.argv.slice(2);

function readStdin() {
  try { return readFileSync(0, 'utf8').replace(/\r?\n$/, ''); }
  catch { return ''; }
}

switch (cmd) {
  case 'status': {
    const p = paths();
    console.log(JSON.stringify({ vaultDir: p.dir, keys: listKeys().length }, null, 2));
    break;
  }
  case 'list': {
    // Print metadata only — no ciphertext, no values.
    console.log(JSON.stringify(listKeys(), null, 2));
    break;
  }
  case 'acl': {
    console.log(JSON.stringify(loadAcl(), null, 2));
    break;
  }
  case 'audit': {
    const n = Number(rest[0] || 20);
    const p = paths();
    let lines = [];
    try { lines = readFileSync(p.audit, 'utf8').trim().split('\n'); } catch { /* none yet */ }
    console.log(lines.slice(-n).join('\n'));
    break;
  }
  case 'grant': {
    const key = rest[0];
    if (!key) { console.error('usage: grant <key> --role r --id id --status s [--break-glass]'); process.exit(2); }
    const opt = (name) => { const i = rest.indexOf(name); return i >= 0 ? rest[i + 1] : undefined; };
    const acl = loadAcl();
    const e = acl.keys[key] || { allowedRoles: [], allowedAgentIds: [], status: 'active', breakGlass: false };
    if (opt('--role')) e.allowedRoles = [...new Set([...(e.allowedRoles || []), opt('--role')])];
    if (opt('--id')) e.allowedAgentIds = [...new Set([...(e.allowedAgentIds || []), opt('--id')])];
    if (opt('--status')) e.status = opt('--status');
    if (rest.includes('--break-glass')) e.breakGlass = true;
    acl.keys[key] = e;
    saveAcl(acl);
    console.log(JSON.stringify({ key, acl: e }, null, 2));
    break;
  }
  case 'set': {
    const key = rest[0];
    if (!key) { console.error('usage: set <key>   (value on STDIN)'); process.exit(2); }
    const value = readStdin();
    if (!value) { console.error('no value on STDIN'); process.exit(2); }
    const res = putSecret(key, () => value, { by: process.env.PAPERCLIP_AGENT_ID || 'operator' });
    console.log(JSON.stringify(res, null, 2)); // metadata only
    break;
  }
  default:
    console.error('commands: status | list | acl | audit [N] | grant <key> ... | set <key>');
    process.exit(2);
}
