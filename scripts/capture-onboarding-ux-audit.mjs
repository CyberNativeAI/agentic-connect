#!/usr/bin/env node
/**
 * CYB-999208 — capture public onboarding surfaces (live + local) for UX audit.
 * Run: node scripts/capture-onboarding-ux-audit.mjs
 */
import { createServer } from "node:http";
import { mkdir, readFile } from "node:fs/promises";
import { join, extname } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const __dirname = fileURLToPath(new URL(".", import.meta.url));
const repoRoot = join(__dirname, "..");
const launchDir = join(repoRoot, "launch");
const outDir = join(repoRoot, "docs", "ux-audit", "cyb-999208");

const MIME = {
  ".html": "text/html",
  ".css": "text/css",
  ".js": "application/javascript",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".svg": "image/svg+xml"
};

const LIVE_TARGETS = [
  { name: "live-home", url: "https://cybernative.ai/" },
  { name: "live-connect-guide", url: "https://cybernative.ai/connect-ai-agent-to-discourse" },
  { name: "live-getting-started-topic", url: "https://cybernative.ai/t/39309" },
  { name: "live-github-readme", url: "https://github.com/CyberNativeAI/agentic-connect" }
];

const LOCAL_TARGETS = [
  { name: "local-connect-guide", path: "/pages/connect-ai-agent-to-discourse.html" },
  { name: "local-secure-keys", path: "/pages/secure-api-keys-for-ai-agents.html" },
  { name: "local-launch-hub", path: "/index.html" }
];

const VIEWPORTS = [
  { suffix: "desktop", width: 1440, height: 900 },
  { suffix: "mobile", width: 390, height: 844 }
];

await mkdir(outDir, { recursive: true });

function staticServer() {
  return createServer(async (req, res) => {
    const path = (req.url || "/").split("?")[0];
    const filePath = join(launchDir, path === "/" ? "index.html" : path);
    try {
      const body = await readFile(filePath);
      res.writeHead(200, { "Content-Type": MIME[extname(filePath)] || "application/octet-stream" });
      res.end(body);
    } catch {
      res.writeHead(404);
      res.end("Not found");
    }
  });
}

const server = staticServer();
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const port = server.address().port;
const localBase = `http://127.0.0.1:${port}`;

const browser = await chromium.launch();
const manifest = [];

for (const vp of VIEWPORTS) {
  const context = await browser.newContext({
    viewport: { width: vp.width, height: vp.height },
    userAgent: vp.suffix === "mobile"
      ? "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
      : undefined
  });
  const page = await context.newPage();

  for (const target of LIVE_TARGETS) {
    const filename = `${target.name}-${vp.suffix}.png`;
    const filepath = join(outDir, filename);
    try {
      await page.goto(target.url, { waitUntil: "domcontentloaded", timeout: 45000 });
      await page.waitForTimeout(2000);
      await page.screenshot({ path: filepath, fullPage: true });
      const title = await page.title();
      const h1 = await page.locator("h1").first().textContent().catch(() => null);
      manifest.push({ file: filename, source: target.url, title, h1: h1?.trim() || null, status: "ok" });
      console.log(`saved ${filename}`);
    } catch (err) {
      manifest.push({ file: filename, source: target.url, status: "error", error: String(err) });
      console.error(`failed ${filename}:`, err.message);
    }
  }

  for (const target of LOCAL_TARGETS) {
    const filename = `${target.name}-${vp.suffix}.png`;
    const filepath = join(outDir, filename);
    const url = `${localBase}${target.path}`;
    try {
      await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });
      await page.screenshot({ path: filepath, fullPage: true });
      const title = await page.title();
      const h1 = await page.locator("h1").first().textContent().catch(() => null);
      manifest.push({ file: filename, source: url, title, h1: h1?.trim() || null, status: "ok" });
      console.log(`saved ${filename}`);
    } catch (err) {
      manifest.push({ file: filename, source: url, status: "error", error: String(err) });
      console.error(`failed ${filename}:`, err.message);
    }
  }

  await context.close();
}

await browser.close();
server.close();

await import("node:fs/promises").then((fs) =>
  fs.writeFile(join(outDir, "manifest.json"), JSON.stringify(manifest, null, 2))
);
console.log(`\nEvidence written to ${outDir}`);
