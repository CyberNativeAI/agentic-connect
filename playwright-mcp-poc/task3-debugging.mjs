/**
 * Task 3: Debugging path
 *
 * Intentionally triggers page errors and captures console output, network
 * request/response data, and screenshots to prove failures are debuggable
 * from captured evidence.
 *
 * Usage: node playwright-mcp-poc/task3-debugging.mjs
 */

import { chromium } from "playwright";
import { createServer } from "http";
import { mkdirSync, writeFileSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const EVIDENCE_DIR = resolve(__dirname, "evidence");
const SCREENSHOTS_DIR = resolve(__dirname, "screenshots");

mkdirSync(EVIDENCE_DIR, { recursive: true });
mkdirSync(SCREENSHOTS_DIR, { recursive: true });

const timestamp = () => new Date().toISOString().replace(/[:.]/g, "-");

function startLocalServer() {
  return new Promise((resolveServer) => {
    const server = createServer((req, res) => {
      if (req.url === "/404") {
        res.writeHead(404, { "Content-Type": "text/html" });
        res.end(
          "<html><body><h1>404 Not Found</h1><script>console.error('POC_404: Resource not found error')</script></body></html>"
        );
      } else if (req.url === "/error") {
        res.writeHead(500, { "Content-Type": "text/html" });
        res.end(
          "<html><body><h1>500 Server Error</h1><script>throw new Error('POC_500_RUNTIME: Intentional runtime error')</script></body></html>"
        );
      } else if (req.url === "/mixed") {
        res.writeHead(200, { "Content-Type": "text/html" });
        res.end(`<html><body><h1>Test Page</h1><script>
console.log("POC_INFO: Normal info message");
console.warn("POC_WARN: Warning message for debugging");
console.error("POC_ERROR: Error message for debugging");
console.debug("POC_DEBUG: Debug message");
setTimeout(function() { throw new Error("POC_UNHANDLED: Async unhandled error for debugging test"); }, 0);
</script></body></html>`);
      } else {
        res.writeHead(200, { "Content-Type": "text/plain" });
        res.end("ok");
      }
    });

    const PORT = 19999;
    server.listen(PORT, "127.0.0.1", () => {
      resolveServer({ server, baseUrl: `http://127.0.0.1:${PORT}` });
    });
  });
}

async function main() {
  console.log(`=== Task 3: Debugging Path ===`);
  console.log(`Started at: ${new Date().toISOString()}\n`);

  const { server, baseUrl } = await startLocalServer();

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
  });

  const consoleEntries = [];
  const networkEntries = [];
  const pageErrors = [];

  const ts = timestamp();
  let overallStatus = "pass";

  try {
    // --- Scenario 1: Navigate to a 404 page ---
    console.log("--- Scenario 1: 404 page ---");
    const page1 = await context.newPage();
    const page1Console = [];
    page1.on("console", (msg) => {
      consoleEntries.push({ type: msg.type(), text: msg.text(), timestamp: new Date().toISOString() });
      page1Console.push({ type: msg.type(), text: msg.text() });
      console.log(`   [console.${msg.type()}] ${msg.text()}`);
    });
    page1.on("pageerror", (err) => {
      pageErrors.push({ message: err.message, timestamp: new Date().toISOString() });
      console.log(`   [pageerror] ${err.message}`);
    });

    try {
      await page1.goto(`${baseUrl}/404`, { waitUntil: "load", timeout: 10000 });
      console.log("   404 page loaded successfully");
    } catch (e) {
      console.log(`   404 page navigation issue: ${e.message.split("\n")[0]}`);
    }

    // Screenshot of 404 page
    try {
      await page1.screenshot({ path: resolve(SCREENSHOTS_DIR, `task3-404-${ts}.png`) });
      console.log("   404 screenshot saved");
    } catch (_) {}

    // --- Scenario 2: 500 error page with JS runtime error ---
    console.log("\n--- Scenario 2: 500 error with JS runtime error ---");
    const page2 = await context.newPage();
    const page2Console = [];
    const page2Errors = [];
    page2.on("console", (msg) => {
      consoleEntries.push({ type: msg.type(), text: msg.text(), timestamp: new Date().toISOString() });
      page2Console.push({ type: msg.type(), text: msg.text() });
      console.log(`   [console.${msg.type()}] ${msg.text()}`);
    });
    page2.on("pageerror", (err) => {
      pageErrors.push({ message: err.message, timestamp: new Date().toISOString() });
      page2Errors.push({ message: err.message });
      console.log(`   [pageerror] ${err.message}`);
    });

    try {
      await page2.goto(`${baseUrl}/error`, { waitUntil: "load", timeout: 10000 });
      await page2.waitForTimeout(1000);
      console.log("   500 error page processed");
    } catch (e) {
      console.log(`   500 page issue: ${e.message.split("\n")[0]}`);
    }

    try {
      await page2.screenshot({ path: resolve(SCREENSHOTS_DIR, `task3-500-${ts}.png`) });
      console.log("   500 screenshot saved");
    } catch (_) {}

    // --- Scenario 3: DNS resolution failure ---
    console.log("\n--- Scenario 3: Failed network request (DNS failure) ---");
    const page3 = await context.newPage();
    const netFailures = [];
    page3.on("requestfailed", (req) => {
      const fail = req.failure()?.errorText || "unknown";
      networkEntries.push({ phase: "requestfailed", url: req.url(), failure: fail, timestamp: new Date().toISOString() });
      netFailures.push({ url: req.url(), failure: fail });
      console.log(`   [requestfailed] ${req.url()} - ${fail}`);
    });

    try {
      await page3.goto("https://definitely.invalid.local.test/", { waitUntil: "load", timeout: 10000 });
    } catch (e) {
      console.log(`   Navigation error (expected): ${e.message.split("\n")[0]}`);
    }

    // --- Scenario 4: Mixed console output + unhandled error ---
    console.log("\n--- Scenario 4: Mixed console output + unhandled error ---");
    const page4 = await context.newPage();
    const page4Console = [];
    const page4Errors = [];
    page4.on("console", (msg) => {
      consoleEntries.push({ type: msg.type(), text: msg.text(), timestamp: new Date().toISOString() });
      page4Console.push({ type: msg.type(), text: msg.text() });
      console.log(`   [console.${msg.type()}] ${msg.text()}`);
    });
    page4.on("pageerror", (err) => {
      pageErrors.push({ message: err.message, timestamp: new Date().toISOString() });
      page4Errors.push({ message: err.message });
      console.log(`   [pageerror] ${err.message}`);
    });

    try {
      await page4.goto(`${baseUrl}/mixed`, { waitUntil: "load", timeout: 10000 });
      await page4.waitForTimeout(1000);
    } catch (e) {
      console.log(`   Mixed page issue: ${e.message.split("\n")[0]}`);
    }

    try {
      await page4.screenshot({ path: resolve(SCREENSHOTS_DIR, `task3-mixed-${ts}.png`) });
      console.log("   Mixed page screenshot saved");
    } catch (_) {}

    // --- Evidence summary ---
    console.log("\n--- Evidence Summary ---");
    console.log(`   Console entries: ${consoleEntries.length}`);
    console.log(`   Network failures: ${networkEntries.length}`);
    console.log(`   Page errors: ${pageErrors.length}`);

    const consoleErrors = consoleEntries.filter((e) => e.type === "error");
    const consoleWarnings = consoleEntries.filter((e) => e.type === "warning");
    console.log(`   Console errors: ${consoleErrors.length}`);
    console.log(`   Console warnings: ${consoleWarnings.length}`);

    // --- Debuggability check ---
    const hasConsoleErrors = consoleErrors.length > 0;
    const hasNetworkFailures = networkEntries.length > 0;
    const hasPageErrors = pageErrors.length > 0;

    console.log("\n--- Debuggability Check ---");
    console.log(`   Console errors captured: ${hasConsoleErrors ? "YES" : "NO"}`);
    console.log(`   Network failures captured: ${hasNetworkFailures ? "YES" : "NO"}`);
    console.log(`   Page errors captured: ${hasPageErrors ? "YES" : "NO"}`);

    if (!hasConsoleErrors && !hasNetworkFailures && !hasPageErrors) {
      console.log("\n   WARNING: Some evidence categories empty - check connectivity");
      overallStatus = "partial";
    }

    // --- Save evidence ---
    const evidence = {
      scenario: "CYB-999532 PoC Task 3",
      timestamp: new Date().toISOString(),
      consoleEntries,
      pageErrors,
      networkFailures: networkEntries,
      summary: {
        totalConsole: consoleEntries.length,
        consoleErrors: consoleErrors.length,
        consoleWarnings: consoleWarnings.length,
        networkFailures: networkEntries.length,
        pageErrors: pageErrors.length,
      },
    };

    writeFileSync(resolve(EVIDENCE_DIR, `task3-evidence-${ts}.json`), JSON.stringify(evidence, null, 2));
    console.log(`\nEvidence saved to: task3-evidence-${ts}.json`);

  } catch (err) {
    console.error(`Fatal error: ${err.message}`);
    overallStatus = "fail";
  } finally {
    await browser.close();
    server.close();
  }

  console.log(`\n=== Task 3: ${overallStatus.toUpperCase()} ===`);
  return { status: overallStatus, summary: { consoleEntries: consoleEntries.length, pageErrors: pageErrors.length, networkFailures: networkEntries.length } };
}

main().then((result) => {
  writeFileSync(resolve(EVIDENCE_DIR, `task3-result-${timestamp()}.json`), JSON.stringify(result, null, 2));
  process.exit(0);
});
