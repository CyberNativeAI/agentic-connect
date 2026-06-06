#!/usr/bin/env node
/**
 * CYB-208 evidence capture — run from repo root:
 *   npm init -y && npm install playwright && npx playwright install chromium
 *   node scripts/capture-launch-screenshots.mjs
 */
import { createServer } from "node:http";
import { mkdir, readFile } from "node:fs/promises";
import { join, extname } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const __dirname = fileURLToPath(new URL(".", import.meta.url));
const repoRoot = join(__dirname, "..");
const launchDir = join(repoRoot, "launch");
const evidenceTag = process.env.EVIDENCE_TAG || "cyb-254";
const outDir = join(launchDir, "evidence", evidenceTag);

const MIME = {
  ".html": "text/html",
  ".css": "text/css",
  ".js": "application/javascript",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".svg": "image/svg+xml"
};

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

const pages = [
  { name: "hub", path: "/index.html" },
  { name: "concierge", path: "/concierge.html" },
  { name: "sponsor", path: "/sponsor.html" }
];

const viewports = [
  { suffix: "desktop", width: 1440, height: 900 },
  { suffix: "mobile", width: 390, height: 844 }
];

const server = staticServer();
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const port = server.address().port;
const base = `http://127.0.0.1:${port}`;

const browser = await chromium.launch();
for (const vp of viewports) {
  const context = await browser.newContext({ viewport: { width: vp.width, height: vp.height } });
  const page = await context.newPage();
  for (const item of pages) {
    await page.goto(`${base}${item.path}`, { waitUntil: "networkidle" });
    await page.screenshot({
      path: join(outDir, `${item.name}-${vp.suffix}.png`),
      fullPage: true
    });
    console.log(`saved ${item.name}-${vp.suffix}.png`);
  }
  await context.close();
}
await browser.close();
server.close();
