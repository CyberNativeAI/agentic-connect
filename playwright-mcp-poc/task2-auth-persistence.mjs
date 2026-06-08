/**
 * Task 2: Auth / session persistence
 *
 * Simulates logging into a site, persists browser state to a storage-state
 * file, restarts a new browser session with that state, and verifies the login
 * survives. Uses httpbin.org for a reproducible auth simulation (no real
 * credentials needed).
 *
 * Usage: node playwright-mcp-poc/task2-auth-persistence.mjs
 */

import { chromium } from "playwright";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const EVIDENCE_DIR = resolve(__dirname, "evidence");
const SCREENSHOTS_DIR = resolve(__dirname, "screenshots");
const STORAGE_STATE_DIR = resolve(__dirname, "storage-state");

mkdirSync(EVIDENCE_DIR, { recursive: true });
mkdirSync(SCREENSHOTS_DIR, { recursive: true });
mkdirSync(STORAGE_STATE_DIR, { recursive: true });

const STORAGE_STATE_PATH = resolve(STORAGE_STATE_DIR, "session.json");
const COOKIE_DOMAIN = "httpbin.org";
const timestamp = () => new Date().toISOString().replace(/[:.]/g, "-");

function uid() {
  return `poc-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

async function main() {
  console.log(`=== Task 2: Auth / Session Persistence ===`);
  console.log(`Started at: ${new Date().toISOString()}\n`);

  const results = { steps: [] };

  // --- Phase 1: Simulate login and save storage state ---
  console.log("--- Phase 1: Simulate login and persist state ---");

  const browser1 = await chromium.launch({ headless: true });
  const context1 = await browser1.newContext({
    viewport: { width: 1280, height: 720 },
  });
  const page1 = await context1.newPage();

  try {
    const sessionToken = uid();
    console.log(`1. Setting up auth session...`);
    console.log(`   Session token: ${sessionToken}`);

    // Set localStorage item (simulates a post-login token)
    await page1.goto(`https://${COOKIE_DOMAIN}`, { waitUntil: "domcontentloaded" });
    await page1.evaluate(
      ({ token, domain }) => {
        localStorage.setItem("auth_token", token);
        localStorage.setItem("auth_user", "poc-agent");
        localStorage.setItem("auth_scope", "read,write");
        localStorage.setItem("auth_expires", String(Date.now() + 86400000));
      },
      { token: sessionToken, domain: COOKIE_DOMAIN }
    );

    // Set a cookie (simulates session cookie)
    await context1.addCookies([
      {
        name: "session",
        value: sessionToken,
        domain: `.${COOKIE_DOMAIN}`,
        path: "/",
        httpOnly: true,
        secure: true,
        sameSite: "Lax",
      },
      {
        name: "user_prefs",
        value: JSON.stringify({ theme: "dark", lang: "en" }),
        domain: `.${COOKIE_DOMAIN}`,
        path: "/",
      },
    ]);

    console.log("   Set localStorage keys: auth_token, auth_user, auth_scope, auth_expires");
    console.log("   Set cookies: session, user_prefs");

    // Verify login state is present in this session
    const verify1 = await page1.evaluate(() => ({
      auth_token: localStorage.getItem("auth_token"),
      auth_user: localStorage.getItem("auth_user"),
      auth_scope: localStorage.getItem("auth_scope"),
    }));
    console.log(`   Verify in-session: auth_token=${verify1.auth_token?.slice(0, 10)}...`);

    // Save storage state
    await context1.storageState({ path: STORAGE_STATE_PATH });
    console.log(`2. Storage state saved to: ${STORAGE_STATE_PATH}`);

    const stateSize = readFileSync(STORAGE_STATE_PATH).length;
    console.log(`   State file size: ${stateSize} bytes`);

    results.steps.push({
      phase: "login-and-save",
      token: sessionToken,
      storageStatePath: STORAGE_STATE_PATH,
      stateSize,
      status: "pass",
    });

    // Screenshot after login
    const preScreenshot = resolve(SCREENSHOTS_DIR, `task2-after-login-${timestamp()}.png`);
    await page1.screenshot({ path: preScreenshot });
    console.log(`3. Screenshot after login: ${preScreenshot}`);
  } catch (err) {
    console.error(`Phase 1 FAIL: ${err.message}`);
    results.steps.push({ phase: "login-and-save", error: err.message, status: "fail" });
  } finally {
    await browser1.close();
  }

  // --- Phase 2: New session with stored state ---
  console.log("\n--- Phase 2: Restart with persisted state ---");

  if (!existsSync(STORAGE_STATE_PATH)) {
    console.error("FAIL: Storage state file not found - cannot verify persistence");
    results.steps.push({ phase: "verify-persistence", error: "State file missing", status: "fail" });
    return { status: "fail", results };
  }

  const browser2 = await chromium.launch({ headless: true });
  const context2 = await browser2.newContext({
    viewport: { width: 1280, height: 720 },
    storageState: STORAGE_STATE_PATH, // Load persisted state
  });
  const page2 = await context2.newPage();

  try {
    console.log("4. Creating new browser context with storageState...");

    await page2.goto(`https://${COOKIE_DOMAIN}`, { waitUntil: "domcontentloaded" });

    // Verify localStorage survived
    const verify2 = await page2.evaluate(() => ({
      auth_token: localStorage.getItem("auth_token"),
      auth_user: localStorage.getItem("auth_user"),
      auth_scope: localStorage.getItem("auth_scope"),
      auth_expires: localStorage.getItem("auth_expires"),
    }));

    console.log(`   localStorage auth_token: ${verify2.auth_token ? "PRESENT" : "MISSING"}`);
    console.log(`   localStorage auth_user: ${verify2.auth_user || "MISSING"}`);
    console.log(`   localStorage auth_scope: ${verify2.auth_scope || "MISSING"}`);
    console.log(`   localStorage auth_expires: ${verify2.auth_expires || "MISSING"}`);

    // Verify cookies survived
    const cookies = await context2.cookies();
    const sessionCookie = cookies.find((c) => c.name === "session");
    const prefsCookie = cookies.find((c) => c.name === "user_prefs");

    console.log(`   Cookie 'session': ${sessionCookie ? `PRESENT (${sessionCookie.value.slice(0, 10)}...)` : "MISSING"}`);
    console.log(`   Cookie 'user_prefs': ${prefsCookie ? "PRESENT" : "MISSING"}`);
    console.log(`   Total cookies: ${cookies.length}`);

    // Determine pass/fail
    const allPresent =
      verify2.auth_token &&
      verify2.auth_user &&
      sessionCookie &&
      prefsCookie;

    const phase2Status = allPresent ? "pass" : "fail";
    console.log(`\n5. Persistence verification: ${phase2Status.toUpperCase()}`);

    // Screenshot after restore
    const postScreenshot = resolve(SCREENSHOTS_DIR, `task2-after-restore-${timestamp()}.png`);
    await page2.screenshot({ path: postScreenshot });
    console.log(`6. Screenshot after restore: ${postScreenshot}`);

    results.steps.push({
      phase: "verify-persistence",
      localStorage: verify2,
      cookies: cookies.map((c) => ({ name: c.name, domain: c.domain })),
      allPresent,
      status: phase2Status,
    });
  } catch (err) {
    console.error(`Phase 2 FAIL: ${err.message}`);
    results.steps.push({ phase: "verify-persistence", error: err.message, status: "fail" });
  } finally {
    await browser2.close();
  }

  // --- Phase 3: Verify secrets NOT in state file ---
  console.log("\n--- Phase 3: Secrets hygiene check ---");

  try {
    const stateRaw = readFileSync(STORAGE_STATE_PATH, "utf-8");
    const hasApiKey = /api[_-]?key/i.test(stateRaw);
    const hasSecret = /secret/i.test(stateRaw);
    const hasPassword = /password/i.test(stateRaw);

    console.log(`   State contains 'api_key': ${hasApiKey ? "WARNING" : "clean"}`);
    console.log(`   State contains 'secret': ${hasSecret ? "WARNING" : "clean"}`);
    console.log(`   State contains 'password': ${hasPassword ? "WARNING" : "clean"}`);

    results.steps.push({
      phase: "secrets-hygiene",
      hasApiKey,
      hasSecret,
      hasPassword,
      clean: !hasApiKey && !hasPassword,
      status: !hasApiKey && !hasPassword ? "pass" : "warning",
    });
  } catch (err) {
    console.error(`Phase 3 FAIL: ${err.message}`);
  }

  const overall = results.steps.every((s) => s.status === "pass");
  console.log(`\n=== Task 2: ${overall ? "PASS" : "FAIL or WARNING"} ===`);

  return { status: overall ? "pass" : "fail", results };
}

main().then((result) => {
  writeFileSync(
    resolve(EVIDENCE_DIR, `task2-result-${timestamp()}.json`),
    JSON.stringify(result, null, 2)
  );
  process.exit(result.status === "pass" ? 0 : 1);
});
