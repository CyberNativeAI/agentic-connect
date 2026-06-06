#!/usr/bin/env node
/**
 * CYB-274 — render launch/share assets from HTML source templates.
 * Usage: node scripts/render-cyb274-assets.mjs
 */
import { chromium } from "playwright";
import path from "node:path";
import { fileURLToPath } from "node:url";
import fs from "node:fs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "..");
const sourceDir = path.join(repoRoot, "launch", "assets", "source");
const outDir = path.join(repoRoot, "launch", "assets");

const specs = [
  { html: "og-concierge.html", out: "og-concierge-1200x630.png", width: 1200, height: 630 },
  { html: "og-launch-hub.html", out: "og-launch-hub-1200x630.png", width: 1200, height: 630 },
  { html: "hero-concierge.html", out: "cybernative-concierge-hero.png", width: 1280, height: 720 },
  { html: "hero-sponsor.html", out: "cybernative-sponsor-hero.png", width: 1280, height: 720 },
  { html: "forum-api-key-security.html", out: "forum-header-api-key-security-1200x400.png", width: 1200, height: 400 },
  { html: "forum-mcp-security.html", out: "forum-header-mcp-security-1200x400.png", width: 1200, height: 400 },
  { html: "forum-agentic-connect.html", out: "forum-header-agentic-connect-1200x400.png", width: 1200, height: 400 },
];

fs.mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ deviceScaleFactor: 2 });

for (const spec of specs) {
  const htmlPath = path.join(sourceDir, spec.html);
  const outPath = path.join(outDir, spec.out);
  await page.setViewportSize({ width: spec.width, height: spec.height });
  await page.goto(`file://${htmlPath}`, { waitUntil: "networkidle" });
  await page.screenshot({
    path: outPath,
    clip: { x: 0, y: 0, width: spec.width, height: spec.height },
  });
  console.log(`Wrote ${outPath}`);
}

await browser.close();
