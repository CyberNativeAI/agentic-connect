const { chromium } = require("playwright");
const { resolve, join, dirname } = require("path");
const { mkdirSync } = require("fs");

(async () => {
  const rootDir = resolve(__dirname, "..");
  const browser = await chromium.launch({ headless: true });
  const pages = [
    { url: `file:///${join(rootDir, "launch/pages/connect-ai-agent-to-discourse.html")}`, name: "seo-landing", width: 1280, height: 900 },
    { url: `file:///${join(rootDir, "launch/consultation.html")}`, name: "consultation", width: 1280, height: 900 },
    { url: `file:///${join(rootDir, "launch/consultation.html")}`, name: "consultation-mobile", width: 390, height: 844 },
    { url: `file:///${join(rootDir, "launch/pages/connect-ai-agent-to-discourse.html")}`, name: "seo-landing-mobile", width: 390, height: 844 }
  ];

  const screenshotsDir = join(rootDir, "docs/ux-audit/cyb-999447");
  mkdirSync(screenshotsDir, { recursive: true });

  for (const page of pages) {
    const ctx = await browser.newContext({
      viewport: { width: page.width, height: page.height },
      colorScheme: "dark"
    });
    const p = await ctx.newPage();
    await p.goto(page.url, { waitUntil: "networkidle", timeout: 15000 });
    await p.screenshot({ path: join(screenshotsDir, `${page.name}.png`), fullPage: true });
    console.log(`Captured: ${page.name}`);
    await ctx.close();
  }

  await browser.close();
})();
