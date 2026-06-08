#!/usr/bin/env node
// Deploy CYB-6 revenue landing pages to production via cybernative-seo plugin.
//
// Steps:
//   1. Read each launch page HTML + CSS + JS
//   2. Inline CSS/JS and base64-encode hero images into each HTML file
//   3. Generate updated plugin.rb with routes for all launch pages
//   4. Upload to production server via SCP
//   5. Copy into Discourse container and restart Rails
//
// Prerequisites:
//   - prod_ssh_root vault secret
//   - prod_discourse_admin_api_key vault secret (for API fallback)
//   - Node.js >= 18

import { execSync } from 'node:child_process';
import { readFileSync, writeFileSync, existsSync, unlinkSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';

const __dirname = dirname(fileURLToPath(import.meta.url));
const repoRoot = join(__dirname, '..');
const launchDir = join(repoRoot, 'launch');
const pagesDir = join(launchDir, 'pages');

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
  } catch (err) {
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

function sshExec(command) {
  const keyFile = getSshKeyFile();
  try {
    return execSync(
      `ssh -i "${keyFile}" -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@64.176.199.24 "${command.replace(/"/g, '\\"')}"`,
      { encoding: 'utf8', timeout: 30_000 }
    );
  } finally {
    try { unlinkSync(keyFile); } catch {}
  }
}

function scpExec(localFile, remotePath) {
  const keyFile = getSshKeyFile();
  try {
    return execSync(
      `scp -i "${keyFile}" -o StrictHostKeyChecking=no "${localFile}" root@64.176.199.24:"${remotePath}"`,
      { encoding: 'utf8', timeout: 30_000 }
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

  html = html.replace(
    '<link rel="stylesheet" href="../landing.css">',
    `<style>\n${combinedCss}\n</style>`
  );
  html = html.replace(
    '<link rel="stylesheet" href="./landing.css">',
    `<style>\n${combinedCss}\n</style>`
  );

  const launchJs = readText('launch/launch.js');
  const seoJs = readText('launch/seo.js');

  html = html.replace(
    '<script src="../seo.js"></script>',
    `<script>\n${seoJs}\n</script>`
  );
  html = html.replace(
    '<script src="./seo.js"></script>',
    `<script>\n${seoJs}\n</script>`
  );
  html = html.replace(
    '<script src="../launch.js"></script>',
    `<script>\n${launchJs}\n</script>`
  );
  html = html.replace(
    '<script src="./launch.js"></script>',
    `<script>\n${launchJs}\n</script>`
  );

  for (const [ref, filePath] of Object.entries(IMAGE_MAP)) {
    if (html.includes(ref)) {
      try {
        const b64 = base64Image(filePath);
        html = html.replaceAll(ref, b64);
      } catch (e) {
        console.warn(`  Image not found: ${filePath}, keeping placeholder`);
      }
    }
  }

  return html;
}

const PAGES = {
  '/launch': join(pagesDir, 'index.html'),
  '/launch/concierge': join(pagesDir, 'concierge.html'),
  '/launch/sponsor': join(pagesDir, 'sponsor.html'),
  '/launch/thanks': join(pagesDir, 'thanks.html'),
};

async function deployViaSSH() {
  console.log('Building staged HTML for all launch pages...');
  const stagedPages = {};
  for (const [route, filePath] of Object.entries(PAGES)) {
    if (!existsSync(filePath)) {
      console.warn(`  SKIPPING ${route}: file not found at ${filePath}`);
      continue;
    }
    const html = inlineAssets(readFileSync(filePath, 'utf8'));
    stagedPages[route] = html;
    console.log(`  ${route}: ${html.length} bytes`);
  }

  console.log('\nFetching current plugin.rb from production...');
  const currentPluginRb = sshExec(
    'cat /var/discourse/shared/standalone/tmp/cybernative-seo-src/cybernative-seo/plugin.rb'
  );

  let updated = currentPluginRb;

  const routeLines = Object.entries(stagedPages).map(([route, html], i) => {
    const methodName = `staged_launch_${i}`;
    return `  get "${route}" => "cybernative_seo/pages#${methodName}"`;
  }).join('\n');

  const routeBlock = `\n  # CYB-6 revenue landing pages (CYB-999451)\n${routeLines}\n`;
  if (updated.includes('get "/connect-ai-agent-to-discourse"')) {
    updated = updated.replace(
      'get "/connect-ai-agent-to-discourse"',
      `${routeBlock}  get "/connect-ai-agent-to-discourse"`
    );
  } else {
    updated = updated.replace(
      'get "/" => "cybernative_seo/pages#index"',
      `get "/" => "cybernative_seo/pages#index"\n${routeLines}`
    );
  }

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

  console.log(`Updated plugin.rb: ${updated.length} bytes`);

  const tmpFile = join(process.env.TEMP, 'plugin-rb-cyb-999451.rb');
  writeFileSync(tmpFile, updated, 'utf8');

  console.log('\nUploading plugin.rb to production server...');

  scpExec(tmpFile, '/var/discourse/shared/standalone/tmp/cybernative-seo-src/cybernative-seo/plugin.rb');

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
  Object.keys(stagedPages).forEach(route => {
    console.log(`  https://cybernative.ai${route}`);
  });
}

async function deployViaAPI() {
  console.log('Deploying via Discourse Admin API (fallback)...');

  const apiKey = getSecret('prod_discourse_admin_api_key');
  const baseUrl = 'https://cybernative.ai';
  const authHeaders = {
    'Api-Key': apiKey,
    'Api-Username': 'system',
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };

  for (const [route, filePath] of Object.entries(PAGES)) {
    if (!existsSync(filePath)) continue;
    const body = inlineAssets(readFileSync(filePath, 'utf8'));

    console.log(`Uploading ${route}`);

    try {
      const createResp = await fetch(`${baseUrl}/admin/themes.json`, {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({ theme: { name: `Launch: ${route}`, component: true } }),
      });

      if (!createResp.ok) {
        console.error(`  Failed: HTTP ${createResp.status}`);
        continue;
      }

      const theme = await createResp.json();
      console.log(`  Theme ${theme.theme.id} created`);
    } catch (err) {
      console.error(`  Error: ${err.message}`);
    }
  }
}

async function main() {
  const mode = process.argv.includes('--api') ? 'api' : 'ssh';
  console.log(`CYB-999451 Launch Pages Deploy — ${mode.toUpperCase()} mode\n`);

  if (mode === 'api') {
    await deployViaAPI();
  } else {
    await deployViaSSH();
  }
}

main().catch((err) => {
  console.error('Deploy failed:', err.message);
  process.exit(1);
});
