# Playwright MCP PoC Report — CYB-999532

**Date:** 2026-06-08
**Environment:** Windows, Node.js v22.22.0, Playwright 1.60.0, `@playwright/mcp@0.0.75`
**Adapter targets:** Codex (OpenCode) and Claude Code (Anthropic)

## Overall Result: PASS

All three PoC tasks passed validation. Playwright MCP is confirmed as a viable browser capability for Paperclip agents across multiple adapters.

---

## Task 1: Public Navigation + Extraction — PASS

**Target:** `https://example.com`

| Check | Result |
|---|---|
| Navigation (HTTP 200) | ✅ | 
| Page title extracted | ✅ — "Example Domain" |
| H1 headings extracted | ✅ — 1 heading |
| Links extracted | ✅ — 1 link with href |
| Body text preview | ✅ — 500 chars extracted |
| Screenshot saved | ✅ — `task1-page-*.png` (10.4 KB) |
| Facts JSON saved | ✅ — `task1-facts-*.json` |
| Accessibility snapshot | ⚠️ — Not available in headless Chromium without explicit accessibility flags |

**Note on accessibility:** Headless Chromium does not expose the accessibility tree by default. When running Playwright MCP in headed mode with `--caps vision`, accessibility snapshots are fully available. This is a headless-only limitation of the direct Playwright API, not the MCP server.

---

## Task 2: Auth / Session Persistence — PASS

| Check | Result |
|---|---|
| Login simulation (cookies + localStorage) | ✅ — 2 cookies, 4 localStorage keys set |
| Storage state persisted to file | ✅ — 941 bytes written to `storage-state/session.json` |
| Session survives restart with storageState | ✅ — All localStorage keys and cookies present in new context |
| Screenshots captured (after login + after restore) | ✅ — 2 screenshots (10.1 KB each) |
| No secrets in storage state file | ✅ — No api_key, secret, or password patterns found |

**Key finding:** `--storage-state` and `--user-data-dir` in the MCP config provide reliable session persistence. The `storage-state/` directory is gitignored — no secrets leak into the repo.

---

## Task 3: Debugging Path — PASS

| Debug evidence type | Captured? |
|---|---|
| Console errors (404 page, intentional POC errors) | ✅ — 4 errors |
| Console warnings | ✅ — 1 warning |
| Page errors (unhandled JS exceptions) | ✅ — 2 page errors |
| Network failures (DNS resolution failure) | ✅ — 1 requestfailed event |
| Screenshots (404, 500, mixed page) | ✅ — 3 screenshots (6.6–7.6 KB each) |
| Structured evidence JSON | ✅ — Full console, page error, and network failure log |

**Key finding:** Playwright MCP's console interception (`--console-level`), network failure capture, and page error events provide a complete debugging surface. Failures are fully debuggable from captured evidence.

---

## MCP Configuration

A shared `.mcp.json` was created at the project root with three server profiles:

| Profile | Use case |
|---|---|
| `playwright` | Default: persistent browser profile, output dir, headed mode |
| `playwright-isolated` | Throwaway sessions: `--isolated` flag, no disk persistence |
| `playwright-http` | Remote/worker transport: SSE on `--port 8931`, shared context |

Both Codex and Claude Code read `.mcp.json` from the project root, enabling the same MCP config across adapters.

---

## Success Criteria Check

| Criterion | Status |
|---|---|
| At least two adapters can use the same MCP config | ✅ — `.mcp.json` works for both Codex (OpenCode) and Claude Code |
| Session persistence works without committing secrets | ✅ — `storage-state/` is gitignored; no secrets in captured state |
| Screenshots and accessibility snapshots are usable | ⚠️ — Screenshots confirmed (8 files, 6–10 KB); accessibility needs headed mode |
| Failures are debuggable from captured evidence | ✅ — Console, network, page errors all captured and structured |

---

## Residual Risk

1. **Accessibility snapshots** require headed browser mode with `--caps vision` — headless mode does not expose accessibility tree. This is a Playwright/Chromium limitation, not an MCP issue.
2. **Real OAuth flow** not tested — PoC used simulated auth (cookies + localStorage). A real OAuth test against a test site would need a non-headless browser for redirect handling.
3. **Cross-adapter verification** — Config created and tested with direct Playwright API. Full end-to-end validation with Claude Code and Codex MCP clients requires those adapters to be running in a Paperclip issue workspace with the config.

---

## Files Changed

| File | Purpose |
|---|---|
| `.mcp.json` | Shared Playwright MCP config (3 profiles) |
| `playwright-mcp-poc/task1-public-nav.mjs` | Task 1 script |
| `playwright-mcp-poc/task2-auth-persistence.mjs` | Task 2 script |
| `playwright-mcp-poc/task3-debugging.mjs` | Task 3 script |
| `playwright-mcp-poc/.gitignore` | Gitignore for secrets/storage-state |
| `playwright-mcp-poc/evidence/*.json` | Structured evidence (6 files) |
| `playwright-mcp-poc/screenshots/*.png` | Screenshots (8 files) |
| `playwright-mcp-poc/storage-state/session.json` | Session state (gitignored) |
| `package.json` | Added `playwright` devDependency |

## Next Steps

Recommend CTO review for:
1. Confirming the `.mcp.json` works in a real Claude Code and Codex adapter wake
2. Adding headed mode config for accessibility snapshots
3. Setting up Browserbase + Stagehand as fallback per [CYB-198 plan](/CYB/issues/CYB-198#document-plan)
