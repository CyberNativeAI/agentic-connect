#!/usr/bin/env node
// Deploy CYB-6 revenue landing pages to production via cybernative-seo plugin.
//
// Uses staged HTML files on disk (see LESSONS.md) — never inline HTML into plugin.rb.
// Pattern matches scripts/deploy-cyb-999210-connect-guide.mjs.
//
// Steps:
//   1. Build staged HTML per page (inline CSS/JS + base64 hero images)
//   2. Upload to plugins/cybernative-seo/staged/launch/*.html via SCP
//   3. Patch plugin.rb with small route + staged_launch action (no HTML in Ruby)
//   4. docker cp into Discourse container and touch tmp/restart.txt
//
// Prerequisites:
//   - prod_ssh_root vault secret (ed25519 private key)
//   - Node.js >= 18
//
// Usage:
//   node scripts/deploy-cyb-999451-launch-pages.mjs           # deploy via SSH
//   node scripts/deploy-cyb-999451-launch-pages.mjs --dry-run # build only, no SSH

import { execSync } from 'node:child_process';
import { readFileSync, writeFileSync, existsSync, unlinkSync, mkdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';

const __dirname = dirname(fileURLToPath(import.meta.url));
const repoRoot = join(__dirname, '..');
const pagesDir = join(repoRoot, 'launch', 'pages');

const SRC_DIR = '/var/discourse/shared/standalone/tmp/cybernative-seo-src/cybernative-seo';
const CONTAINER_PATH = 'app:/var/www/discourse/plugins/cybernative-seo';

/** @type {{ route: string, source: string, stagedName: string }[]} */
const PAGES = [
  { route: '/launch', source: join(pagesDir, 'index.html'), stagedName: 'index.html' },
  { route: '/launch/concierge', source: join(pagesDir, 'concierge.html'), stagedName: 'concierge.html' },
  { route: '/launch/sponsor', source: join(pagesDir, 'sponsor.html'), stagedName: 'sponsor.html' },
  { route: '/launch/consultation', source: join(repoRoot, 'launch', 'consultation.html'), stagedName: 'consultation.html' },
  { route: '/launch/thanks', source: join(pagesDir, 'thanks.html'), stagedName: 'thanks.html' },
];

function readText(relPath) {
  return readFileSync(join(repoRoot, relPath), 'utf8');
}

function readBinary(relPath) {
  return readFileSync(join(repoRoot, relPath));
}

function getSecret(key) {
  const p = join(repoRoot, 'secrets-manager');
  try {
    return execSync(`node get-secret.mjs ${key}`, {
      cwd: p, encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'], timeout: 10_000,
    }).trim();
  } catch {
    console.error(`Failed to retrieve secret "${key}"`);
    process.exit(1);
  }
}

function getSshKeyFile() {
  const cred = getSecret('prod_ssh_root');
  const keyFile = join(tmpdir(), 'ssh-key-cyb999451');
  writeFileSync(keyFile, cred + '\n', { encoding: 'utf8', mode: 0o600 });
  return keyFile;
}

function sshExec(command, opts = {}) {
  const keyFile = getSshKeyFile();
  try {
    return execSync(
      `ssh -i "${keyFile}" -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@64.176.199.24 "${command.replace(/"/g, '\\"')}"`,
      { encoding: 'utf8', timeout: opts.timeout || 30_000, stdio: ['pipe', 'pipe', 'pipe'] }
    );
  } finally {
    try { unlinkSync(keyFile); } catch {}
  }
}

function scpFile(localPath, remotePath) {
  const keyFile = getSshKeyFile();
  try {
    execSync(
      `scp -i "${keyFile}" -o StrictHostKeyChecking=no "${localPath}" root@64.176.199.24:"${remotePath}"`,
      { encoding: 'utf8', timeout: 30_000, stdio: ['pipe', 'pipe', 'pipe'] }
    );
  } finally {
    try { unlinkSync(keyFile); } catch {}
  }
}

const IMAGE_MAP = {
  './assets/cybernative-concierge-hero.png': 'launch/assets/cybernative-concierge-hero.png',
  './assets/cybernative-sponsor-hero.png': 'launch/assets/cybernative-sponsor-hero.png',
  './assets/cybernative-agent-launch-hero.png': 'launch/assets/cybernative-agent-launch-hero.png',
};

function base64Image(relPath) {
  const buf = readBinary(relPath);
  const ext = relPath.split('.').pop();
  const mime = ext === 'png' ? 'image/png' : 'image/jpeg';
  return `data:${mime};base64,${buf.toString('base64')}`;
}

function inlineAssets(html) {
  const designTokensCss = readText('launch/design-tokens.css')
    .replace(/@import url\(.*fonts\.googleapis\.com.*\);/, '');
  const landingCss = readText('launch/landing.css')
    .replace(/@import url\("\.\/design-tokens\.css"\);/, '');
  const combinedCss = designTokensCss + '\n' + landingCss;

  for (const href of ['../landing.css', './landing.css']) {
    html = html.replace(
      `<link rel="stylesheet" href="${href}">`,
      `<style>\n${combinedCss}\n</style>`
    );
  }

  const launchJs = readText('launch/launch.js');
  const seoJs = readText('launch/seo.js');

  for (const src of ['../seo.js', './seo.js']) {
    html = html.replace(`<script src="${src}"></script>`, `<script>\n${seoJs}\n</script>`);
  }
  for (const src of ['../launch.js', './launch.js']) {
    html = html.replace(`<script src="${src}"></script>`, `<script>\n${launchJs}\n</script>`);
  }

  for (const [ref, filePath] of Object.entries(IMAGE_MAP)) {
    if (html.includes(ref)) {
      try {
        html = html.replaceAll(ref, base64Image(filePath));
      } catch {
        console.warn(`  Image not found: ${filePath}, keeping placeholder`);
      }
    }
  }

  return html;
}

function buildStagedPages() {
  const staged = [];
  for (const page of PAGES) {
    if (!existsSync(page.source)) {
      console.warn(`  SKIPPING ${page.route}: missing ${page.source}`);
      continue;
    }
    const html = inlineAssets(readFileSync(page.source, 'utf8'));
    staged.push({ ...page, html, bytes: html.length });
    console.log(`  ${page.route} -> staged/launch/${page.stagedName}: ${html.length} bytes`);
  }
  return staged;
}

function writeLocalDryRun(staged) {
  const outDir = join(repoRoot, 'tmp', 'cyb-999451-staged');
  mkdirSync(outDir, { recursive: true });
  for (const page of staged) {
    writeFileSync(join(outDir, page.stagedName), page.html, 'utf8');
  }
  console.log(`\nDry-run output: ${outDir}`);
}

function patchPluginScript() {
  const routeLines = PAGES.map((p) => {
    const launchPage = p.stagedName.replace('.html', '');
    return `    get "${p.route}" => "cybernative_seo/pages#staged_launch", defaults: { launch_page: "${launchPage}" }`;
  }).join('\n');

  return `#!/bin/bash
set -euo pipefail
PLUGIN="${SRC_DIR}/plugin.rb"
BACKUP="${SRC_DIR}/plugin.rb.bak.cyb999451"

cp "$PLUGIN" "$BACKUP"

# Remove legacy inline-HTML launch methods from failed deploy attempts
sed -i '/def staged_launch_[0-9]/,/^  end$/d' "$PLUGIN" || true
sed -i '/# CYB-6 revenue landing pages/d' "$PLUGIN" || true
sed -i '/get "\\/launch/d' "$PLUGIN" || true

if ! grep -q 'def staged_launch' "$PLUGIN"; then
  sed -i '/^    def html_sitemap/i\\
    def staged_launch\\
      launch_page = params[:launch_page].to_s\\
      return raise Discourse::NotFound if launch_page.empty? || launch_page.include?("..")\\
      staged_file = File.join(Rails.root, "plugins", "cybernative-seo", "staged", "launch", "\#{launch_page}.html")\\
      if File.exist?(staged_file)\\
        return render html: File.read(staged_file).html_safe, layout: false, content_type: "text/html"\\
      end\\
      raise Discourse::NotFound\\
    end\\
' "$PLUGIN"
fi

if ! grep -q 'staged_launch.*launch_page: "index"' "$PLUGIN"; then
  sed -i '/get "\\/connect-ai-agent-to-discourse"/i\\
  # CYB-6 revenue landing pages (CYB-999451 staged files)\\
${routeLines}\\
' "$PLUGIN"
fi

echo "plugin.rb patched ($(wc -c < "$PLUGIN") bytes)"
`;
}

function deployViaSSH(staged) {
  const localStaging = join(tmpdir(), 'cyb-999451-launch-staged');
  mkdirSync(join(localStaging, 'launch'), { recursive: true });

  console.log('\nUploading staged HTML to server...');
  sshExec(`mkdir -p ${SRC_DIR}/staged/launch`);

  for (const page of staged) {
    const localFile = join(localStaging, 'launch', page.stagedName);
    writeFileSync(localFile, page.html, 'utf8');
    scpFile(localFile, `${SRC_DIR}/staged/launch/${page.stagedName}`);
  }

  console.log('Patching plugin.rb (routes + staged_launch only)...');
  const patchScript = patchPluginScript();
  const patchFile = join(tmpdir(), 'patch-cyb999451.sh');
  writeFileSync(patchFile, patchScript, 'utf8');
  scpFile(patchFile, `${SRC_DIR}/patch-cyb999451.sh`);
  sshExec(`bash ${SRC_DIR}/patch-cyb999451.sh`);
  try { unlinkSync(patchFile); } catch {}

  console.log('Copying plugin + staged files into Discourse container...');
  sshExec(
    `docker cp ${SRC_DIR}/plugin.rb ${CONTAINER_PATH}/plugin.rb && docker cp ${SRC_DIR}/staged/launch ${CONTAINER_PATH}/staged/launch`
  );

  console.log('Restarting Discourse Rails app...');
  const result = sshExec('docker exec app touch /var/www/discourse/tmp/restart.txt');
  console.log(`Restart result: ${result.trim()}`);

  console.log('\n=== DEPLOY COMPLETE ===');
  for (const page of staged) {
    console.log(`  https://cybernative.ai${page.route}`);
  }
}

function main() {
  const dryRun = process.argv.includes('--dry-run');
  console.log(`CYB-999451 Launch Pages Deploy${dryRun ? ' (DRY RUN)' : ''}\n`);
  console.log('Building staged HTML...');
  const staged = buildStagedPages();
  if (staged.length === 0) {
    console.error('No pages built — aborting.');
    process.exit(1);
  }

  if (dryRun) {
    writeLocalDryRun(staged);
    return;
  }

  deployViaSSH(staged);
}

main();
