#!/usr/bin/env node
// Deploy CYB-999451 launch pages to cybernative.ai production.
//
// Two deploy modes:
//   1. SSH   - node deploy-cyb-999451-launch-pages.mjs --ssh
//   2. API   - node deploy-cyb-999451-launch-pages.mjs --api (default)
//
// Prerequisites:
//   - prod_ssh_root vault secret (SSH mode)
//   - prod_discourse_admin_api_key vault secret (API mode)
//   - Node.js >= 18

import { execSync } from 'node:child_process';
import { readFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const repoRoot = join(__dirname, '..');
const launchDir = join(repoRoot, 'launch');
const pagesDir = join(launchDir, 'pages');

const PAGES = [
  { file: 'index.html',       route: '/launch',              title: 'Launch offers hub' },
  { file: 'concierge.html',   route: '/launch/concierge',     title: 'Agent Launch Concierge' },
  { file: 'sponsor.html',     route: '/launch/sponsor',       title: 'Sponsored Builder Launch' },
  { file: 'thanks.html',      route: '/launch/thanks',        title: 'Thank you' },
  { file: 'connect-ai-agent-to-discourse.html', route: '/connect-ai-agent-to-discourse', title: 'Connect AI Agent to Discourse' },
];

function getSecret(name) {
  const getSecretPath = join(repoRoot, 'secrets-manager', 'get-secret.mjs');
  try {
    return execSync(`node "${getSecretPath}" ${name}`, {
      cwd: join(repoRoot, 'secrets-manager'),
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'pipe'],
      timeout: 10_000,
    }).trim();
  } catch (err) {
    console.error(`Failed to retrieve secret "${name}": ${err.stderr || err.message}`);
    process.exit(1);
  }
}

function readTextFile(path) {
  if (!existsSync(path)) {
    console.error(`File not found: ${path}`);
    process.exit(1);
  }
  return readFileSync(path, 'utf8');
}

function inlinePage(htmlPath) {
  const html = readTextFile(htmlPath);

  const pageDir = launchDir;
  const landingCss = readTextFile(join(pageDir, 'landing.css'));
  const tokensCss = readTextFile(join(pageDir, 'design-tokens.css'));
  const fullCss = `${tokensCss}\n${landingCss}`;

  const cssRef = /<link rel="stylesheet" href="[^"]*landing\.css[^"]*">/;
  const seoJs = readTextFile(join(pageDir, 'seo.js'));
  const launchJs = readTextFile(join(pageDir, 'launch.js'));

  let result = html.replace(cssRef, `<style>\n${fullCss}\n</style>`);
  result = result.replace(
    /<script src="[^"]*seo\.js[^"]*"><\/script>/,
    `<script>\n${seoJs}\n</script>`
  );
  result = result.replace(
    /<script src="[^"]*launch\.js[^"]*"><\/script>/,
    `<script>\n${launchJs}\n</script>`
  );

  return result;
}

async function deployViaAPI() {
  console.log('Deploying via Discourse Admin API...');

  const apiKey = getSecret('prod_discourse_admin_api_key');
  const baseUrl = 'https://cybernative.ai';
  const authHeaders = {
    'Api-Key': apiKey,
    'Api-Username': 'system',
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };

  for (const page of PAGES) {
    const pagePath = join(pagesDir, page.file);
    const body = inlinePage(pagePath);

    console.log(`Uploading ${page.file} -> ${page.route}`);

    const formData = new FormData();
    formData.append('theme[name]', 'Launch Pages (CYB-999451)');
    formData.append('theme[component]', 'true');

    try {
      const createResp = await fetch(`${baseUrl}/admin/themes.json`, {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({
          theme: {
            name: `Launch: ${page.title}`,
            component: true,
          },
        }),
      });

      if (!createResp.ok) {
        const err = await createResp.text();
        console.error(`  Failed to create theme for ${page.file}: HTTP ${createResp.status} ${err}`);
        continue;
      }

      const theme = await createResp.json();
      const themeId = theme.theme.id;

      await fetch(`${baseUrl}/admin/themes/${themeId}/setting`, {
        method: 'PUT',
        headers: authHeaders,
        body: JSON.stringify({
          name: 'enabled',
          value: 'true',
        }),
      });

      console.log(`  Theme ${themeId} created: "${page.title}"`);
    } catch (err) {
      console.error(`  Error uploading ${page.file}: ${err.message}`);
    }
  }

  console.log('API deploy complete.');
}

async function deployViaSSH() {
  console.log('Deploying via SSH to 64.176.199.24...');

  const sshPass = getSecret('prod_ssh_root');
  const host = '64.176.199.24';
  const user = 'root';

  const tmpDir = '/tmp/cyb999451-launch/';
  const targetDir = '/var/www/cybernative/launch/';

  const filesToCopy = [
    { src: join(launchDir, 'design-tokens.css'), dest: 'design-tokens.css' },
    { src: join(launchDir, 'landing.css'), dest: 'landing.css' },
    { src: join(launchDir, 'launch.js'), dest: 'launch.js' },
    { src: join(launchDir, 'seo.js'), dest: 'seo.js' },
  ];

  for (const page of PAGES) {
    filesToCopy.push({
      src: join(pagesDir, page.file),
      dest: `pages/${page.file}`,
    });
  }

  function ssh(cmd) {
    const sshCmd = `sshpass -p '${sshPass}' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 ${user}@${host} "${cmd}"`;
    try {
      return execSync(sshCmd, { encoding: 'utf8', timeout: 30_000 });
    } catch (err) {
      console.error(`SSH command failed: ${cmd}`);
      throw err;
    }
  }

  console.log(`Creating target directory: ${targetDir}`);
  ssh(`mkdir -p ${targetDir}/pages`);

  for (const f of filesToCopy) {
    const dest = `${targetDir}${f.dest}`;
    console.log(`Copying ${f.dest}`);
    try {
      execSync(
        `sshpass -p '${sshPass}' scp -o StrictHostKeyChecking=no "${f.src}" ${user}@${host}:${dest}`,
        { timeout: 15_000 }
      );
    } catch (err) {
      console.error(`  Failed to copy ${f.dest}: ${err.message}`);
    }
  }

  console.log('SSH deploy complete.');
}

async function main() {
  const mode = process.argv.includes('--ssh') ? 'ssh' : 'api';
  console.log(`CYB-999451 Launch Pages Deploy — ${mode.toUpperCase()} mode`);

  if (mode === 'ssh') {
    await deployViaSSH();
  } else {
    await deployViaAPI();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
