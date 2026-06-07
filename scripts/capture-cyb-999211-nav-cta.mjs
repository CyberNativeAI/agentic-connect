#!/usr/bin/env node
/**
 * CYB-999211 — capture homepage header CTA evidence (before/after deploy).
 * Run: node scripts/capture-cyb-999211-nav-cta.mjs [--phase before|after]
 */
import { mkdir, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const phase = process.argv.includes("--phase")
  ? process.argv[process.argv.indexOf("--phase") + 1]
  : "before";

const __dirname = fileURLToPath(new URL(".", import.meta.url));
const outDir = join(__dirname, "..", "docs", "ux-audit", "cyb-999211", phase);

const VIEWPORTS = [
  { suffix: "desktop", width: 1440, height: 900 },
  { suffix: "mobile", width: 390, height: 844 },
];

const HOMEPAGE_URL = "https://cybernative.ai/";

await mkdir(outDir, { recursive: true });

const browser = await chromium.launch();
const manifest = [];

for (const vp of VIEWPORTS) {
  const context = await browser.newContext({
    viewport: { width: vp.width, height: vp.height },
    userAgent:
      vp.suffix === "mobile"
        ? "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        : undefined,
  });
  const page = await context.newPage();

  const filename = `homepage-${vp.suffix}.png`;
  const filepath = join(outDir, filename);

  try {
    await page.goto(HOMEPAGE_URL, { waitUntil: "domcontentloaded", timeout: 45000 });
    await page.waitForTimeout(2000);

    const probe = await page.evaluate(() => {
      const builderLink =
        document.querySelector(".cn-builder-nav") ||
        [...document.querySelectorAll("a")].find((a) =>
          /connect your agent|connect agent/i.test(a.textContent || "")
        );
      const header = document.querySelector(".d-header");
      const rect = builderLink?.getBoundingClientRect();
      const headerRect = header?.getBoundingClientRect();
      return {
        isAnon: document.documentElement.classList.contains("anon"),
        hasBuilderNav: !!builderLink,
        builderNavText: builderLink?.textContent?.trim() || null,
        builderNavHref: builderLink?.getAttribute("href") || null,
        builderNavVisibleWithoutScroll:
          !!rect && rect.top >= 0 && rect.bottom <= window.innerHeight,
        headerHeight: headerRect?.height ?? null,
        viewportHeight: window.innerHeight,
      };
    });

    await page.screenshot({ path: filepath, fullPage: false });

    manifest.push({
      file: filename,
      phase,
      source: HOMEPAGE_URL,
      viewport: vp.suffix,
      status: "ok",
      ...probe,
    });
    console.log(`saved ${phase}/${filename}`, probe);
  } catch (err) {
    manifest.push({
      file: filename,
      phase,
      source: HOMEPAGE_URL,
      viewport: vp.suffix,
      status: "error",
      error: String(err),
    });
    console.error(`failed ${filename}:`, err.message);
  }

  await context.close();
}

await browser.close();
await writeFile(join(outDir, "manifest.json"), JSON.stringify(manifest, null, 2));
console.log(`\nEvidence written to ${outDir}`);
