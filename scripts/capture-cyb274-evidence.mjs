#!/usr/bin/env node
/**
 * CYB-274 evidence — screenshot one-pager + OG assets for review.
 */
import { chromium } from "playwright";
import path from "node:path";
import { fileURLToPath } from "node:url";
import fs from "node:fs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "..");
const launchDir = path.join(repoRoot, "launch");
const evidenceDir = path.join(launchDir, "evidence", "cyb-274");

fs.mkdirSync(evidenceDir, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage();

const onePager = `file://${path.join(launchDir, "concierge-onepager.html")}`;
for (const viewport of [
  { name: "desktop", width: 1440, height: 900 },
  { name: "mobile", width: 390, height: 844 },
]) {
  await page.setViewportSize({ width: viewport.width, height: viewport.height });
  await page.goto(onePager, { waitUntil: "networkidle" });
  await page.screenshot({
    path: path.join(evidenceDir, `concierge-onepager-${viewport.name}.png`),
    fullPage: true,
  });
  console.log(`Wrote concierge-onepager-${viewport.name}.png`);
}

for (const asset of ["og-concierge-1200x630.png", "forum-header-api-key-security-1200x400.png"]) {
  const assetPath = path.join(launchDir, "assets", asset);
  await page.setViewportSize({ width: 1200, height: asset.includes("400") ? 400 : 630 });
  await page.goto(`file://${assetPath}`);
  await page.screenshot({
    path: path.join(evidenceDir, `preview-${asset}`),
  });
  console.log(`Wrote preview-${asset}`);
}

await browser.close();
