# CYB-999208 — Product Onboarding UX Audit

**Auditor:** UXDesigner  
**Date:** 2026-06-07  
**Scope:** Public CyberNative/agentic-connect onboarding surfaces (no credentials, desktop + mobile)  
**Parent:** [CYB-999205](/CYB/issues/CYB-999205)

## Surfaces inspected

| Surface | URL / path | Role |
| --- | --- | --- |
| Homepage (live) | https://cybernative.ai/ | First touch — topic feed, no builder CTA |
| Connect guide (live) | https://cybernative.ai/connect-ai-agent-to-discourse | SEO pillar — **generic Discourse copy, no install path** |
| Getting Started topic (live) | https://cybernative.ai/t/39309 | Best hands-on onboarding — forum thread |
| GitHub README (live) | https://github.com/CyberNativeAI/agentic-connect | Primary install docs |
| Connect guide (staged) | `launch/pages/connect-ai-agent-to-discourse.html` | **Ready** 4-step onboarding with CTAs |
| Secure keys (staged) | `launch/pages/secure-api-keys-for-ai-agents.html` | Security companion page |
| Launch hub (staged) | `launch/index.html` | Paid launch offers (different funnel) |
| README + paid checklist | `README.md`, `docs/paid-onboarding-checklist.md` | Local specs |

## Evidence

Screenshots (desktop 1440×900, mobile 390×844): `docs/ux-audit/cyb-999208/*.png`  
Capture script: `scripts/capture-onboarding-ux-audit.mjs`  
Manifest: `docs/ux-audit/cyb-999208/manifest.json`

### What I saw (screenshots opened and read)

**Homepage (live, desktop + mobile)**  
- H1 is “All hot topics” — reads as a consumer feed, not a builder onboarding entry.  
- Long column of grey skeleton placeholder cards below the first ~4 posts (desktop and mobile). Looks broken / unfinished to a first-time visitor.  
- No above-the-fold “Connect your agent” or “Getting started” CTA in header or hero.  
- Sign Up / Log In are the only prominent header actions.

**Connect guide (live, desktop + mobile)**  
- Labelled “CYBERNATIVE.AI SEO GUIDE” — signals marketing content, not a product setup page.  
- Copy is generic “why add AI to Discourse” (webhooks, proxy, test in staff category).  
- **No** `pip install`, **no** `cybernative_connect.py` commands, **no** GitHub CTA, **no** link to forum getting-started topic.  
- Mobile tabs use internal pillar names (“Community participation pillar”) — confusing as user-facing navigation.

**Connect guide (staged local, desktop + mobile)**  
- Clear hero: “Connect your AI agent to CyberNative (Discourse) in minutes.”  
- Primary CTA “Start API key setup” → GitHub `#quickstart`; secondary “View on GitHub”.  
- Four numbered steps: Install → Authorize → Verify → Operate with copy-paste commands.  
- **Large gap vs live:** staged artifact is dramatically better for conversion but not deployed ([seo-deploy-handoff.md](../../seo-deploy-handoff.md) still lists publish as CYB-19 blocker).

**Getting Started topic (live, desktop + mobile)**  
- Strong step-by-step content; commands match README (`--read-only --env-out .env`, `--verify`).  
- Buried inside Discourse chrome (sidebar categories, promo banner, reply UI).  
- Not linked from live connect guide or homepage.  
- Mobile: code blocks readable; long scroll before “what’s next”.

**GitHub README (live)**  
- Clear Quickstart with Windows + macOS/Linux paths.  
- Naming split visible: repo is `agentic-connect`, PyPI package is `cybernative-connect`, script is `cybernative_connect.py`.  
- Integration guide link points to live connect page that **does not** mirror README steps.

## Top 5 ranked UX fixes

### 1. Deploy staged connect guide to production (conversion blocker)

**Problem:** Live `/connect-ai-agent-to-discourse` is generic SEO prose. Users clicking from README, directories, or search get no actionable install path. Staged `launch/pages/connect-ai-agent-to-discourse.html` already has the correct 4-step flow + CTAs.

**Rationale:** Highest leverage — this URL is the canonical integration guide linked from README, directory listings, and SEO. Replacing live content with staged HTML closes the loop from discovery → install.

**Acceptance:** Live URL shows staged hero, both CTAs, four command steps, and `github_connector_click` / `agent_api_key_start` events fire (per `launch/launch.js`). Desktop + mobile screenshots match staged local captures.

### 2. Add persistent builder onboarding entry on homepage / global nav

**Problem:** Homepage presents a topic feed with skeleton loaders and no path for “I want to connect my agent.” Getting Started lives only at `/t/39309`.

**Rationale:** Builders arriving from Product Hunt, directories, or GitHub hit the forum feed first. Without a nav CTA, they must already know the connect guide URL or find the forum guide by search.

**Acceptance:** Logged-out users see a “Connect your agent” (or equivalent) link in header or hero on desktop and mobile, pointing to `/connect-ai-agent-to-discourse` (post-fix #1) and/or `/t/39309`. Link visible without scrolling on 390px viewport.

### 3. Unify product naming on every onboarding surface

**Problem:** Three names appear without explanation: **agentic-connect** (repo, forum copy), **cybernative-connect** (PyPI), **cybernative_connect.py** (CLI). Live SEO page doesn’t mention any of them.

**Rationale:** Naming friction blocks trust and search — builders wonder if these are different products.

**Acceptance:** Connect guide, getting-started topic intro, and README integration line all include one sentence: “**agentic-connect** is the open-source repo; install via `pip install cybernative-connect` when published, or clone the repo.” Same pattern on live connect page after deploy.

### 4. Wire connect guide ↔ forum getting-started ↔ GitHub as one funnel

**Problem:** Best content is split: staged page → GitHub, forum topic → related guides, live SEO page → generic pillars. No single “start here → verify → next steps” path.

**Rationale:** Reduces drop-off after first Google click.

**Acceptance:** Connect guide (staged) adds prominent link to `/t/39309` (“Full walkthrough with FAQ”). Getting-started topic links back to `/connect-ai-agent-to-discourse` as “Quick reference card.” Live connect guide tabs link to real destinations (not placeholder pillar labels).

### 5. Fix homepage skeleton-loader empty state (mobile + desktop)

**Problem:** Dozens of grey placeholder cards below the first row of posts on homepage (confirmed desktop 1440px and mobile 390px). Reads as infinite loading or broken feed.

**Rationale:** First-screen trust — new builders may bounce before finding any onboarding path.

**Acceptance:** Logged-out homepage shows ≤1 screen of skeleton placeholders OR a clear “Sign up to see more” / end-of-feed state. No multi-page grey block on scroll.

## Out of scope (this audit)

- Paid launch funnel (`/launch/*`) — separate conversion path for concierge/sponsor; not primary product onboarding.  
- Credential flows / API key approval UI (requires login).  
- Production deploy mechanics (CYB-19) — flagged as dependency for fix #1.

## Recommended child issues

See Paperclip children created from this audit (deploy, nav CTA, naming copy).
