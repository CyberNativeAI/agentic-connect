#!/usr/bin/env node
// Deploy staged SEO pages to production (CYB-999210).
// Uploads inlined HTML + patches plugin.rb to serve staged files from disk.

import { execSync } from 'node:child_process';
import { readFileSync, writeFileSync, unlinkSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';

const __dirname = dirname(fileURLToPath(import.meta.url));
const workspaceRoot = join(__dirname, '..');

const SRC_DIR = '/var/discourse/shared/standalone/tmp/cybernative-seo-src/cybernative-seo';
const CONTAINER_PATH = 'app:/var/www/discourse/plugins/cybernative-seo';

const PAGES = [
  { slug: 'connect-ai-agent-to-discourse', file: 'launch/pages/connect-ai-agent-to-discourse.html', desc: 'Connect guide' },
  { slug: 'ai-agent-social-network', file: 'launch/pages/ai-agent-social-network.html', desc: 'Agent social network' },
  { slug: 'secure-api-keys-for-ai-agents', file: 'launch/pages/secure-api-keys-for-ai-agents.html', desc: 'Secure API keys' },
];

function readText(relPath) {
  return readFileSync(join(workspaceRoot, relPath), 'utf8');
}

function getSecret(key) {
  const p = join(workspaceRoot, 'secrets-manager');
  return execSync(`node get-secret.mjs ${key}`, { cwd: p, encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'] }).trim();
}

function getSshIdentity() {
  const cred = getSecret('prod_ssh_root');
  if (cred.startsWith('-----BEGIN')) {
    const keyFile = join(tmpdir(), 'ssh-key-deploy');
    writeFileSync(keyFile, cred + '\n', { encoding: 'utf8', mode: 0o600 });
    return { type: 'key', keyFile };
  }
  return { type: 'password', value: cred };
}

function execSSH(cmd, opts = {}) {
  const identity = getSshIdentity();
  let sshArgs = '-o StrictHostKeyChecking=no -o ConnectTimeout=10';
  let env = { ...process.env };
  if (identity.type === 'key') {
    sshArgs += ` -i "${identity.keyFile}"`;
  } else {
    const ps1 = join(tmpdir(), 'ssh-ap.ps1');
    const enc = Buffer.from(identity.value, 'utf8').toString('base64');
    writeFileSync(ps1, `$p=[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('${enc}'));Write-Output $p`, 'utf8');
    env.SSH_ASKPASS = `powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "${ps1}"`;
    env.DISPLAY = 'dummy'; env.SSH_ASKPASS_REQUIRE = 'force';
  }
  try {
    return execSync(`ssh ${sshArgs} root@64.176.199.24 "${cmd.replace(/"/g, '\\"')}"`, { env, encoding: 'utf8', timeout: opts.timeout || 60000, stdio: ['pipe', 'pipe', 'pipe'] });
  } finally {
    if (identity.type === 'key') try { unlinkSync(identity.keyFile); } catch {}
  }
}

function execSCP(local, remote) {
  const identity = getSshIdentity();
  let scpArgs = '-o StrictHostKeyChecking=no';
  let env = { ...process.env };
  if (identity.type === 'key') { scpArgs += ` -i "${identity.keyFile}"`; }
  try {
    execSync(`scp ${scpArgs} "${local}" root@64.176.199.24:"${remote}"`, { env, encoding: 'utf8', timeout: 60000, stdio: ['pipe', 'pipe', 'pipe'] });
  } finally {
    if (identity.type === 'key') try { unlinkSync(identity.keyFile); } catch {}
  }
}

function buildHtml(pageFile) {
  const designTokensCss = readText('launch/design-tokens.css').replace(/@import url\(.*fonts\.googleapis\.com.*\);/, '');
  const landingCss = readText('launch/landing.css').replace(/@import url\("\.\/design-tokens\.css"\);/, '');
  const seoJs = readText('launch/seo.js');
  const launchJs = readText('launch/launch.js');

  let html = readText(pageFile);
  const combinedCss = designTokensCss + '\n' + landingCss;
  html = html.replace('<link rel="stylesheet" href="../landing.css">', `<style>\n${combinedCss}\n</style>`);
  html = html.replace('<script src="../seo.js"></script>', `<script>\n${seoJs}\n</script>`);
  html = html.replace('<script src="../launch.js"></script>', `<script>\n${launchJs}\n</script>`);
  return html;
}

function main() {
  // Build staged HTML for all pages
  const tmpHtmls = [];
  for (const page of PAGES) {
    console.log(`Building ${page.desc} (${page.slug})...`);
    const html = buildHtml(page.file);
    console.log(`  ${html.length} bytes`);
    const tmpFile = join(tmpdir(), `${page.slug}.html`);
    writeFileSync(tmpFile, html, 'utf8');
    tmpHtmls.push({ slug: page.slug, tmpFile });
  }

  console.log('\nConnecting to server...');
  execSSH(`mkdir -p ${SRC_DIR}/staged`);

  console.log('Uploading staged HTML files...');
  for (const { slug, tmpFile } of tmpHtmls) {
    execSCP(tmpFile, `${SRC_DIR}/staged/${slug}.html`);
    console.log(`  Uploaded ${slug}.html`);
  }

  console.log('Patching plugin.rb...');
  const slugChecks = PAGES.map(p =>
    `      if params[:slug] == "${p.slug}"\n` +
    `        staged_file = File.join(Rails.root, "plugins", "cybernative-seo", "staged", "${p.slug}.html")\n` +
    `        if File.exist?(staged_file)\n` +
    `          return render html: File.read(staged_file).html_safe, layout: false, content_type: "text/html"\n` +
    `        end\n` +
    `      end`
  ).join('\n');

  const patch = `set -e
PLUGIN="${SRC_DIR}/plugin.rb"
BACKUP="${SRC_DIR}/plugin.rb.bak.cyb999210"
cp "$PLUGIN" "$BACKUP"

sed -i '/staged_connect/d' "$PLUGIN"
sed -i '/staged_html/d' "$PLUGIN"
sed -i 's|get "/connect-ai-agent-to-discourse" => "cybernative_seo/pages#staged_connect"||' "$PLUGIN"

for slug in ${PAGES.map(p => p.slug).join(' ')}; do
  route="get \\"/\\$slug\\" => \\"cybernative_seo/pages#show\\", defaults: { slug: \\"\\$slug\\" }"
  if ! grep -q "$slug.*cybernative_seo/pages" "$PLUGIN"; then
    sed -i "/^    get \\"\\/smart-pages\\/index\\"/i\\\\    $route" "$PLUGIN" 2>/dev/null || true
  fi
done

if ! grep -q 'staged_file = File.join.*Rails.root.*staged' "$PLUGIN"; then
  sed -i '/^    def show$/a\\\\n${slugChecks.split('\n').map(l => '\\' + l).join('\n')}' "$PLUGIN"
fi

grep -c "staged_file" "$PLUGIN"
echo "Patch complete"`;

  const patchFile = join(tmpdir(), 'cyb999210-patch.sh');
  writeFileSync(patchFile, patch, 'utf8');
  execSCP(patchFile, `${SRC_DIR}/cyb999210-patch.sh`);
  execSSH(`bash ${SRC_DIR}/cyb999210-patch.sh`);
  try { unlinkSync(patchFile); } catch {}

  console.log('Copying plugin into Discourse container...');
  execSSH(`docker cp ${SRC_DIR}/plugin.rb ${CONTAINER_PATH}/plugin.rb && docker cp ${SRC_DIR}/staged ${CONTAINER_PATH}/staged`);

  console.log('Restarting Discourse Rails...');
  execSSH('docker exec app touch /var/www/discourse/tmp/restart.txt');

  for (const { tmpFile } of tmpHtmls) try { unlinkSync(tmpFile); } catch {}

  console.log('\n=== DEPLOY COMPLETE ===');
  for (const page of PAGES) {
    console.log(`  https://cybernative.ai/${page.slug}`);
  }
}

main();