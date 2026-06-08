#!/usr/bin/env node
// Deploy staged agent onboarding connect guide to production.
// CYB-999210 — updates cybernative-seo Discourse plugin to serve staged HTML.
//
// Steps:
//   1. Build the plugin.rb update with inlined staged HTML + CSS + JS
//   2. Upload to production server
//   3. Copy into Discourse container
//   4. Restart Rails app

import { execSync } from 'node:child_process';
import { readFileSync, writeFileSync, unlinkSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';

const __dirname = dirname(fileURLToPath(import.meta.url));
const workspaceRoot = join(__dirname, '..');

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

function sshExec(command) {
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
      { env, encoding: 'utf8', timeout: 30000, stdio: ['pipe', 'pipe', 'pipe'] }
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

function buildPluginRb(stagedHtml) {
  const currentPluginRb = sshExec(
    'cat /var/discourse/shared/standalone/tmp/cybernative-seo-src/cybernative-seo/plugin.rb'
  );

  const escapedHtml = stagedHtml
    .replace(/\\/g, '\\\\')
    .replace(/"/g, '\\"')
    .replace(/\n/g, '\\n')
    .replace(/\r/g, '');

  const stagedMethod = `
  def staged_connect
    staged_html = "${escapedHtml}"
    render html: staged_html.html_safe, layout: false, content_type: "text/html"
  end`;

  let updated = currentPluginRb;

  updated = updated.replace(
    /get "\/connect-ai-agent-to-discourse" => "cybernative_seo\/pages#show", defaults: { slug: "connect-ai-agent-to-discourse" }/,
    'get "/connect-ai-agent-to-discourse" => "cybernative_seo/pages#staged_connect"'
  );

  updated = updated.replace(
    '    def html_sitemap',
    `${stagedMethod}\n\n    def html_sitemap`
  );

  return updated;
}

function main() {
  console.log('Building staged HTML with inlined CSS/JS...');
  const stagedHtml = buildStagedHtml();
  console.log(`Staged HTML: ${stagedHtml.length} bytes`);

  console.log('\nBuilding updated plugin.rb...');
  const pluginRb = buildPluginRb(stagedHtml);
  console.log(`Updated plugin.rb: ${pluginRb.length} bytes`);

  const tmpFile = join(tmpdir(), 'plugin-rb-cyb-999210.rb');
  writeFileSync(tmpFile, pluginRb, 'utf8');
  console.log(`Wrote plugin.rb to ${tmpFile}`);

  console.log('\nUploading plugin.rb to production server...');
  scpFile(tmpFile, '/var/discourse/shared/standalone/tmp/cybernative-seo-src/cybernative-seo/plugin.rb');

  console.log('Copying plugin into Discourse container...');
  sshExec(
    'docker cp /var/discourse/shared/standalone/tmp/cybernative-seo-src/cybernative-seo/plugin.rb app:/var/www/discourse/plugins/cybernative-seo/plugin.rb'
  );

  console.log('Restarting Discourse Rails app...');
  const result = sshExec(
    'docker exec app touch /var/www/discourse/tmp/restart.txt'
  );
  console.log(`Restart result: ${result.trim()}`);

  try { unlinkSync(tmpFile); } catch {}

  console.log('\n=== DEPLOY COMPLETE ===');
  console.log('Verify: https://cybernative.ai/connect-ai-agent-to-discourse');
}

main();
