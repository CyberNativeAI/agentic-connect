// Per-agent secrets vault — core library.
//
// SECURITY INVARIANTS (see DESIGN.md):
//   * Secret VALUES never appear in source, logs, audit records, or stdout.
//     This file only ever moves opaque buffers between disk and a caller that
//     has already passed an ACL check. It never console.log()s a plaintext.
//   * On-disk format: AES-256-GCM, one random 96-bit IV per secret, auth tag
//     stored alongside ciphertext. Master key is a 32-byte file, mode 0600.
//   * The vault data dir is OUTSIDE any git repo (instance-level) so encrypted
//     blobs are never committed.
//
// No third-party dependencies — Node built-ins only.

import { randomBytes, createCipheriv, createDecipheriv } from 'node:crypto';
import { readFileSync, writeFileSync, existsSync, mkdirSync, appendFileSync, chmodSync } from 'node:fs';
import { join, dirname } from 'node:path';

const ALGO = 'aes-256-gcm';

// Resolve the vault directory. Defaults to the instance-level secrets dir so
// the encrypted store lives next to the runtime's existing master.key and is
// shared across agent workspaces — never inside a workspace/git repo.
export function vaultDir() {
  return process.env.PAPERCLIP_AGENT_VAULT_DIR
    || join(process.env.PAPERCLIP_INSTANCE_DIR
        || 'C:\\Users\\andru\\.paperclip\\instances\\default',
      'secrets', 'agent-vault');
}

function paths() {
  const dir = vaultDir();
  return {
    dir,
    keyFile: join(dir, 'vault.key'),
    store: join(dir, 'vault.enc'),
    acl: join(dir, 'acl.json'),
    audit: join(dir, 'audit.log'),
  };
}

function ensureDir(dir) {
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
}

// Lazily create a 256-bit master key on first use. The key file is the single
// thing an operator must protect; losing it loses the vault (by design).
export function ensureMasterKey() {
  const p = paths();
  ensureDir(p.dir);
  if (!existsSync(p.keyFile)) {
    writeFileSync(p.keyFile, randomBytes(32));
    try { chmodSync(p.keyFile, 0o600); } catch { /* best-effort on Windows */ }
  }
  const key = readFileSync(p.keyFile);
  if (key.length !== 32) throw new Error('vault.key must be exactly 32 bytes');
  return key;
}

function loadStore() {
  const p = paths();
  if (!existsSync(p.store)) return { version: 1, secrets: {} };
  return JSON.parse(readFileSync(p.store, 'utf8'));
}

function saveStore(store) {
  const p = paths();
  ensureDir(p.dir);
  writeFileSync(p.store, JSON.stringify(store, null, 2));
  try { chmodSync(p.store, 0o600); } catch { /* best-effort */ }
}

export function loadAcl() {
  const p = paths();
  if (!existsSync(p.acl)) return { version: 1, keys: {} };
  return JSON.parse(readFileSync(p.acl, 'utf8'));
}

export function saveAcl(acl) {
  const p = paths();
  ensureDir(p.dir);
  writeFileSync(p.acl, JSON.stringify(acl, null, 2));
}

// Append-only audit trail. Records WHO asked for WHICH key, WHEN, and the
// DECISION — never the value. One JSON object per line.
export function audit(entry) {
  const p = paths();
  ensureDir(p.dir);
  const line = JSON.stringify({ ts: new Date().toISOString(), ...entry }) + '\n';
  appendFileSync(p.audit, line);
}

// ---- crypto ---------------------------------------------------------------

function encrypt(key, plaintext) {
  const iv = randomBytes(12);
  const cipher = createCipheriv(ALGO, key, iv);
  const ct = Buffer.concat([cipher.update(Buffer.from(plaintext, 'utf8')), cipher.final()]);
  const tag = cipher.getAuthTag();
  return { iv: iv.toString('base64'), ct: ct.toString('base64'), tag: tag.toString('base64') };
}

function decrypt(key, rec) {
  const decipher = createDecipheriv(ALGO, key, Buffer.from(rec.iv, 'base64'));
  decipher.setAuthTag(Buffer.from(rec.tag, 'base64'));
  return Buffer.concat([decipher.update(Buffer.from(rec.ct, 'base64')), decipher.final()]).toString('utf8');
}

// ---- public API -----------------------------------------------------------

// Store (or rotate) a secret value under `keyName`. Returns metadata only.
// `valueProvider` is a function returning the plaintext, so callers can pull a
// value from an API response without it ever living in a named variable here.
export function putSecret(keyName, valueProvider, meta = {}) {
  const key = ensureMasterKey();
  const store = loadStore();
  const existed = Boolean(store.secrets[keyName]);
  const now = new Date().toISOString();
  const enc = encrypt(key, valueProvider());
  store.secrets[keyName] = {
    ...enc,
    createdAt: existed ? store.secrets[keyName].createdAt : now,
    rotatedAt: existed ? now : null,
    meta: { ...(existed ? store.secrets[keyName].meta : {}), ...meta },
  };
  saveStore(store);
  audit({ action: existed ? 'rotate' : 'create', key: keyName, by: meta.by || 'system' });
  return { key: keyName, existed, createdAt: store.secrets[keyName].createdAt, rotatedAt: store.secrets[keyName].rotatedAt };
}

// Resolve the effective access decision for (agentId, role, keyName).
export function authorize(acl, keyName, agentId, role) {
  const entry = acl.keys[keyName];
  if (!entry) return { allowed: false, reason: 'unknown_key' };
  if (entry.status && entry.status !== 'active') {
    return { allowed: false, reason: entry.status }; // e.g. pending_ceo_approval
  }
  const byId = (entry.allowedAgentIds || []).includes(agentId);
  const byRole = (entry.allowedRoles || []).includes(role);
  if (byId || byRole) return { allowed: true, breakGlass: Boolean(entry.breakGlass) };
  return { allowed: false, reason: 'not_in_acl' };
}

// Fetch a secret on behalf of a caller. Enforces ACL, writes an audit record,
// and returns the plaintext ONLY to an authorized caller. Throws on denial.
export function getSecret(keyName, { agentId, role }) {
  const acl = loadAcl();
  const decision = authorize(acl, keyName, agentId, role);
  audit({ action: 'access', key: keyName, agentId, role, allowed: decision.allowed,
          reason: decision.reason || (decision.breakGlass ? 'break_glass' : 'ok') });
  if (!decision.allowed) {
    const err = new Error(`access denied for key "${keyName}" (${decision.reason})`);
    err.code = 'EACCES_VAULT';
    throw err;
  }
  const key = ensureMasterKey();
  const store = loadStore();
  const rec = store.secrets[keyName];
  if (!rec) throw new Error(`key "${keyName}" present in ACL but missing from store`);
  return decrypt(key, rec); // plaintext returned to authorized caller only
}

export function listKeys() {
  const store = loadStore();
  const acl = loadAcl();
  return Object.keys({ ...store.secrets, ...acl.keys }).sort().map((k) => ({
    key: k,
    stored: Boolean(store.secrets[k]),
    createdAt: store.secrets[k]?.createdAt || null,
    rotatedAt: store.secrets[k]?.rotatedAt || null,
    acl: acl.keys[k] || null,
  }));
}

export { paths };
