/**
 * Task 1: Public navigation + extraction
 *
 * Loads a live public page, extracts structured facts (page title, headings,
 * links, meta tags), and saves a screenshot.
 *
 * Usage: node playwright-mcp-poc/task1-public-nav.mjs
 */

import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const EVIDENCE_DIR = resolve(__dirname, "evidence");
const SCREENSHOTS_DIR = resolve(__dirname, "screenshots");

mkdirSync(EVIDENCE_DIR, { recursive: true });
mkdirSync(SCREENSHOTS_DIR, { recursive: true });

const TARGET_URL = process.env.POC_TARGET_URL || "https://example.com";

function timestamp() {
  return new Date().toISOString().replace(/[:.]/g, "-");
}

async function main() {
  console.log(`=== Task 1: Public Navigation + Extraction ===`);
  console.log(`Target: ${TARGET_URL}`);
  console.log(`Started at: ${new Date().toISOString()}\n`);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    userAgent:
      "Paperclip-Agent-PoC/1.0 (Playwright MCP validation; +https://paperclip.ing)",
  });
  const page = await context.newPage();

  const consoleMessages = [];
  page.on("console", (msg) => {
    consoleMessages.push({ type: msg.type(), text: msg.text() });
  });

  try {
    // --- Navigate ---
    console.log("1. Navigating to page...");
    const response = await page.goto(TARGET_URL, {
      waitUntil: "networkidle",
      timeout: 30000,
    });
    console.log(`   Status: ${response?.status()} ${response?.statusText()}`);

    // --- Extract structured facts ---
    console.log("\n2. Extracting structured facts...");
    const facts = await page.evaluate(() => {
      const getMeta = (name) => {
        const el = document.querySelector(`meta[name="${name}"], meta[property="${name}"]`);
        return el ? el.getAttribute("content") : null;
      };

      return {
        title: document.title,
        url: location.href,
        h1: [...document.querySelectorAll("h1")].map((e) => e.textContent?.trim()),
        h2: [...document.querySelectorAll("h2")].map((e) => e.textContent?.trim()),
        description: getMeta("description") || getMeta("og:description"),
        ogTitle: getMeta("og:title"),
        ogImage: getMeta("og:image"),
        links: [...document.querySelectorAll("a[href]")]
          .slice(0, 20)
          .map((a) => ({
            text: a.textContent?.trim().slice(0, 80),
            href: a.href,
          })),
        bodyTextPreview: (document.body?.textContent || "").trim().slice(0, 500),
        hasHeaders: !!document.querySelector("header"),
        hasFooter: !!document.querySelector("footer"),
        hasNav: !!document.querySelector("nav"),
      };
    });

    console.log(`   Title: ${facts.title}`);
    console.log(`   URL: ${facts.url}`);
    console.log(`   H1 count: ${facts.h1.length}`);
    console.log(`   H2 count: ${facts.h2.length}`);
    console.log(`   Links extracted: ${facts.links.length}`);
    console.log(`   Description: ${facts.description?.slice(0, 80) || "none"}`);
    console.log(`   Semantic elements - header:${facts.hasHeaders} footer:${facts.hasFooter} nav:${facts.hasNav}`);

    // --- Save facts ---
    const factsFile = resolve(EVIDENCE_DIR, `task1-facts-${timestamp()}.json`);
    writeFileSync(factsFile, JSON.stringify(facts, null, 2));
    console.log(`\n3. Facts saved to: ${factsFile}`);

    // --- Screenshot ---
    const screenshotFile = resolve(SCREENSHOTS_DIR, `task1-page-${timestamp()}.png`);
    await page.screenshot({ path: screenshotFile, fullPage: true });
    console.log(`4. Screenshot saved to: ${screenshotFile}`);

    // --- Accessibility snapshot (simulate what Playwright MCP would provide) ---
    console.log("\n5. Capturing accessibility snapshot...");
    let a11yAvailable = false;
    let a11ySummary = { note: "Accessibility snapshot not available in this configuration" };
    try {
      const snapshot = await page.accessibility.snapshot({ interestingOnly: true });
      if (snapshot) {
        a11yAvailable = true;
        a11ySummary = {
          role: snapshot.role,
          name: snapshot.name,
          childCount: snapshot.children?.length || 0,
          topLevelRoles: (snapshot.children || []).slice(0, 20).map((c) => c.role),
        };
        console.log(`   Root role: ${a11ySummary.role}`);
        console.log(`   Root name: ${a11ySummary.name || "(none)"}`);
        console.log(`   Direct children: ${a11ySummary.childCount}`);

        const a11yFile = resolve(EVIDENCE_DIR, `task1-a11y-${timestamp()}.json`);
        writeFileSync(a11yFile, JSON.stringify({ summary: a11ySummary, snapshot }, null, 2));
        console.log(`   Accessibility snapshot saved to: ${a11yFile}`);
      }
    } catch (a11yErr) {
      console.log(`   Accessibility not available: ${a11yErr.message}`);
    }

    // --- Console evidence ---
    if (consoleMessages.length > 0) {
      const consoleFile = resolve(EVIDENCE_DIR, `task1-console-${timestamp()}.json`);
      writeFileSync(consoleFile, JSON.stringify(consoleMessages, null, 2));
      console.log(`6. Console messages (${consoleMessages.length}) saved to: ${consoleFile}`);
    }

    console.log("\n=== Task 1: PASS ===");
    return { status: "pass", facts, screenshotFile };
  } catch (err) {
    console.error(`\n=== Task 1: FAIL ===`);
    console.error(`Error: ${err.message}`);

    // Capture error screenshot
    try {
      const errFile = resolve(SCREENSHOTS_DIR, `task1-error-${timestamp()}.png`);
      await page.screenshot({ path: errFile });
      console.error(`Error screenshot saved: ${errFile}`);
    } catch (_) {
      /* swallow */
    }

    return { status: "fail", error: err.message };
  } finally {
    await browser.close();
  }
}

main().then((result) => {
  writeFileSync(
    resolve(EVIDENCE_DIR, `task1-result-${timestamp()}.json`),
    JSON.stringify(result, null, 2)
  );
  process.exit(result.status === "pass" ? 0 : 1);
});
