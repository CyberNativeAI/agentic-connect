#!/usr/bin/env node
// Deploy staged agent onboarding connect guide to production.
// CYB-999210 — uploads staged HTML file and patches the cybernative-seo
// Discourse plugin to serve it from disk (no inline HTML in Ruby).

import { execSync } from 'node:child_process';
import { readFileSync, writeFileSync, unlinkSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';

const __dirname = dirname(fileURLToPath(import.meta.url));
const workspaceRoot = join(__dirname, '..');

const SRC_DIR = '/var/discourse/shared/standalone/tmp/cybernative-seo-src/cybernative-seo';
const CONTAINER_PATH = 'app:/var/www/discourse/plugins/cybernative-seo';

function readText(relPath) {
  return readFileSync(join(workspaceRoot, relPath), 'utf8');
}

function getSecret(key) {
  const p = join(workspaceRoot, 'secrets-manager');
  return execSync(`node get-secret.mjs ${key}`, { cwd: p, encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'] }).trim();
}

function createSshAskpass(sshPass) {
  const ps1File = join(tmpdir(), 'ssh-askpass.ps1');
  const encoded = Buffer.from(sshPass, 'utf8').toString('base64');
  writeFileSync(ps1File,
    `$pwd = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('${encoded}'))\nWrite-Output $pwd\n`, 'utf8');
  return ps1File;
}

function sshExec(command, opts = {}) {
  const sshPass = getSecret('prod_ssh_root');
  const askpassScript = createSshAskpass(sshPass);
  const env = {
    ...process.env,
    SSH_ASKPASS: `powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "${askpassScript}"`,
    DISPLAY: 'dummy',
    SSH_ASKPASS_REQUIRE: 'force',
  };
  try {
    const result = execSync(
      `ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@64.176.199.24 "${command.replace(/"/g, '\\"')}"`,
      { env, encoding: 'utf8', timeout: opts.timeout || 30000, stdio: ['pipe', 'pipe', 'pipe'] }
    );
    return result;
  } finally {
    try { unlinkSync(askpassScript); } catch {}
  }
}

function scpFile(localPath, remotePath) {
  const sshPass = getSecret('prod_ssh_root');
  const askpassScript = createSshAskpass(sshPass);
  const env = {
    ...process.env,
    SSH_ASKPASS: `powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "${askpassScript}"`,
    DISPLAY: 'dummy',
    SSH_ASKPASS_REQUIRE: 'force',
  };
  try {
    execSync(
      `scp -o StrictHostKeyChecking=no "${localPath}" root@64.176.199.24:"${remotePath}"`,
      { env, encoding: 'utf8', timeout: 30000, stdio: ['pipe', 'pipe', 'pipe'] }
    );
  } finally {
    try { unlinkSync(askpassScript); } catch {}
  }
}

function buildStagedHtml() {
  const designTokensCss = readText('launch/design-tokens.css')
    .replace(/@import url\(.*fonts\.googleapis\.com.*\);/, '');
  const landingCss = readText('launch/landing.css')
    .replace(/@import url\("\.\/design-tokens\.css"\);/, '');
  const seoJs = readText('launch/seo.js');
  const launchJs = readText('launch/launch.js');

  let html = readText('launch/pages/connect-ai-agent-to-discourse.html');

  const combinedCss = designTokensCss + '\n' + landingCss;
  html = html.replace(
    '<link rel="stylesheet" href="../landing.css">',
    `<style>\n${combinedCss}\n</style>`
  );
  html = html.replace(
    '<script src="../seo.js"></script>',
    `<script>\n${seoJs}\n</script>`
  );
  html = html.replace(
    '<script src="../launch.js"></script>',
    `<script>\n${launchJs}\n</script>`
  );

  return html;
}

function main() {
  console.log('Building staged HTML with inlined CSS/JS...');
  const stagedHtml = buildStagedHtml();
  console.log(`Staged HTML: ${stagedHtml.length} bytes`);

  const tmpHtml = join(tmpdir(), 'connect-ai-agent-to-discourse.html');
  writeFileSync(tmpHtml, stagedHtml, 'utf8');
  console.log(`Wrote staged HTML to ${tmpHtml}`);

  console.log('\nUploading staged HTML to server...');
  sshExec(`mkdir -p ${SRC_DIR}/staged`);
  scpFile(tmpHtml, `${SRC_DIR}/staged/connect-ai-agent-to-discourse.html`);

  console.log('Patching plugin.rb to serve staged file from disk...');

  const patchScript = `
set -e
PLUGIN="${SRC_DIR}/plugin.rb"
BACKUP="${SRC_DIR}/plugin.rb.bak.cyb999210"

cp "$PLUGIN" "$BACKUP"

sed -i '/staged_connect/d' "$PLUGIN"
sed -i 's|get "/connect-ai-agent-to-discourse" => "cybernative_seo/pages#staged_connect"|get "/connect-ai-agent-to-discourse" => "cybernative_seo/pages#show", defaults: { slug: "connect-ai-agent-to-discourse" }|' "$PLUGIN"

if ! grep -q 'staged_file = File.join.*connect-ai-agent-to-discourse' "$PLUGIN"; then
  sed -i '/^    def show$/a\\
      if params[:slug] == "connect-ai-agent-to-discourse"\\
        staged_file = File.join(Rails.root, "plugins", "cybernative-seo", "staged", "connect-ai-agent-to-discourse.html")\\
        if File.exist?(staged_file)\\
          return render html: File.read(staged_file).html_safe, layout: false, content_type: "text/html"\\
        end\\
      end' "$PLUGIN"
fi

echo "Patch complete"
`;

  const patchScriptFile = join(tmpdir(), 'patch-cyb999210.sh');
  writeFileSync(patchScriptFile, patchScript, { encoding: 'utf8' });
  scpFile(patchScriptFile, `${SRC_DIR}/patch-cyb999210.sh`);

  sshExec(`bash ${SRC_DIR}/patch-cyb999210.sh`);
  try { unlinkSync(patchScriptFile); } catch {}

  console.log('Copying plugin into Discourse container...');
  sshExec(
    `docker cp ${SRC_DIR}/plugin.rb ${CONTAINER_PATH}/plugin.rb && docker cp ${SRC_DIR}/staged ${CONTAINER_PATH}/staged`
  );

  console.log('Restarting Discourse Rails app...');
  const result = sshExec(
    'docker exec app touch /var/www/discourse/tmp/restart.txt'
  );
  console.log(`Restart result: ${result.trim()}`);

  try { unlinkSync(tmpHtml); } catch {}

  console.log('\n=== DEPLOY COMPLETE ===');
  console.log('Verify: https://cybernative.ai/connect-ai-agent-to-discourse');
}

main();
