#!/usr/bin/env node
// Deploy CYB-6 revenue landing pages to production via cybernative-seo plugin.
//
// Steps:
//   1. Read each launch page HTML + CSS + JS
//   2. Inline CSS/JS and base64-encode hero images into each HTML file
//   3. Generate updated plugin.rb with routes for all launch pages
//   4. Upload to production server via SCP
//   5. Copy into Discourse container and restart Rails

import { execSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const workspaceRoot = join(__dirname, '..', '..');
const launchDir = join(workspaceRoot, 'launch');

function readText(relPath) {
  return readFileSync(join(workspaceRoot, relPath), 'utf8');
}

function readBinary(relPath) {
  return readFileSync(join(workspaceRoot, relPath));
}

function getSecret(key) {
  const p = join(workspaceRoot, 'agentic-connect', 'secrets-manager');
  return execSync(`node get-secret.mjs ${key}`, { cwd: p, encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'] }).trim();
}

function sshExec(command) {
  const batFile = process.env.TEMP + '\\ssh-askpass.bat';
  const sshPass = getSecret('prod_ssh_root');
  writeFileSync(batFile, `@echo ${sshPass}`);

  const env = {
    ...process.env,
    SSH_ASKPASS: batFile,
    DISPLAY: 'dummy',
    SSH_ASKPASS_REQUIRE: 'force',
  };

  return execSync(
    `ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@64.176.199.24 "${command.replace(/"/g, '\\"')}"`,
    { env, encoding: 'utf8', timeout: 30000 }
  );
}

// Map of image references to their file paths
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
  // Inline CSS
  const designTokensCss = readText('launch/design-tokens.css')
    .replace(/@import url\(.*fonts\.googleapis\.com.*\);/, '');
  const landingCss = readText('launch/landing.css')
    .replace(/@import url\("\.\/design-tokens\.css"\);/, '');
  const combinedCss = designTokensCss + '\n' + landingCss;

  html = html.replace(
    '<link rel="stylesheet" href="./landing.css">',
    `<style>\n${combinedCss}\n</style>`
  );

  // Inline JS
  const launchJs = readText('launch/launch.js');
  html = html.replace(
    '<script src="./launch.js"></script>',
    `<script>\n${launchJs}\n</script>`
  );

  // Base64-encode hero images
  for (const [ref, filePath] of Object.entries(IMAGE_MAP)) {
    if (html.includes(ref)) {
      const b64 = base64Image(filePath);
      html = html.replace(ref, b64);
    }
  }

  return html;
}

// Pages to deploy: route path -> HTML file path
const PAGES = {
  '/launch': 'launch/index.html',
  '/launch/concierge': 'launch/concierge.html',
  '/launch/sponsor': 'launch/sponsor.html',
  '/launch/consultation': 'launch/consultation.html',
  '/launch/thanks': 'launch/thanks.html',
};

function buildStagedHtml(htmlFile) {
  return inlineAssets(readText(htmlFile));
}

function buildPluginRb(stagedPages) {
  const currentPluginRb = sshExec(
    'cat /var/discourse/shared/standalone/tmp/cybernative-seo-src/cybernative-seo/plugin.rb'
  );

  let updated = currentPluginRb;

  // Add route definitions for each launch page
  const routeLines = Object.entries(stagedPages).map(([route, html], i) => {
    const methodName = `staged_launch_${i}`;
    return `  get "${route}" => "cybernative_seo/pages#${methodName}"`;
  }).join('\n');

  // Insert routes before the existing connect-agent route or at the top of the routes section
  const routeBlock = `\n  # CYB-6 revenue landing pages\n${routeLines}\n`;
  updated = updated.replace(
    /get "\/connect-ai-agent-to-discourse"/,
    `${routeBlock}  get "/connect-ai-agent-to-discourse"`
  );

  // Add staged_launch methods before the html_sitemap method
  let methodsBlock = '';
  Object.entries(stagedPages).forEach(([route, html], i) => {
    const methodName = `staged_launch_${i}`;
    const escapedHtml = html
      .replace(/\\/g, '\\\\')
      .replace(/"/g, '\\"')
      .replace(/\n/g, '\\n')
      .replace(/\r/g, '');
    methodsBlock += `
  def ${methodName}
    staged_html = "${escapedHtml}"
    render html: staged_html.html_safe, layout: false, content_type: "text/html"
  end
`;
  });

  updated = updated.replace(
    '    def html_sitemap',
    `${methodsBlock}\n    def html_sitemap`
  );

  return updated;
}

async function main() {
  console.log('Building staged HTML for all launch pages...');
  const stagedPages = {};
  for (const [route, filePath] of Object.entries(PAGES)) {
    const html = buildStagedHtml(filePath);
    stagedPages[route] = html;
    console.log(`  ${route}: ${html.length} bytes`);
  }

  console.log('\nFetching current plugin.rb from production...');
  console.log('Building updated plugin.rb...');
  const pluginRb = buildPluginRb(stagedPages);
  console.log(`Updated plugin.rb: ${pluginRb.length} bytes`);

  // Write the updated plugin.rb to a temp file
  const tmpFile = join(process.env.TEMP, 'plugin-rb-cyb-999451.rb');
  writeFileSync(tmpFile, pluginRb, 'utf8');

  console.log('\nUploading plugin.rb to production server...');
  const batFile = process.env.TEMP + '\\ssh-askpass.bat';
  const sshPass = getSecret('prod_ssh_root');
  writeFileSync(batFile, `@echo ${sshPass}`);

  execSync(
    `scp -o StrictHostKeyChecking=no "${tmpFile}" root@64.176.199.24:/var/discourse/shared/standalone/tmp/cybernative-seo-src/cybernative-seo/plugin.rb`,
    {
      env: {
        ...process.env,
        SSH_ASKPASS: batFile,
        DISPLAY: 'dummy',
        SSH_ASKPASS_REQUIRE: 'force',
      },
      encoding: 'utf8',
      timeout: 30000,
    }
  );

  console.log('Copying plugin into Discourse container...');
  sshExec(
    'docker cp /var/discourse/shared/standalone/tmp/cybernative-seo-src/cybernative-seo/plugin.rb app:/var/www/discourse/plugins/cybernative-seo/plugin.rb'
  );

  console.log('Restarting Discourse Rails app...');
  const result = sshExec(
    "docker exec app /bin/bash -c 'cd /var/www/discourse && touch tmp/restart.txt && echo restarted'"
  );
  console.log(`Restart result: ${result.trim()}`);

  console.log('\n=== DEPLOY COMPLETE ===');
  console.log('Verify the following URLs:');
  Object.keys(stagedPages).forEach(route => {
    console.log(`  https://cybernative.ai${route}`);
  });
}

main().catch((err) => {
  console.error('Deploy failed:', err.message);
  process.exit(1);
});