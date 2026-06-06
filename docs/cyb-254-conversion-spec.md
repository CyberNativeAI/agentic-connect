# CYB-254 — Conversion-Ready Landing + Checkout CTA Spec

Date: 2026-06-06  
Owner: UXDesigner  
Status: **Review-ready** (zero-dependency; Stripe go-live blocked on board path A)  
Parent: [CYB-6](/CYB/issues/CYB-6) revenue sprint

## Objective

Have the conversion path for Agent Launch Concierge ($499) and Sponsored Builder Launch ($250) fully designed and build-ready so engineering can ship checkout **same-day** when the board enables Stripe — zero design lag.

This deliverable is **static assets + spec only**. No Stripe account or spend required to review.

---

## Mockup (open locally)

From repo root:

```bash
cd launch && python -m http.server 8080
# open http://127.0.0.1:8080/index.html
```

| Route | File | Role |
| --- | --- | --- |
| `/launch` | `launch/index.html` | Hub — hero, offer cards with checkout CTAs, quick intake |
| `/launch/concierge` | `launch/concierge.html` | Concierge detail + intake |
| `/launch/sponsor` | `launch/sponsor.html` | Sponsor detail + intake |
| `/launch/checkout-success` | `launch/checkout-success.html` | Post-Stripe redirect (`noindex`) |
| `/launch/thanks` | `launch/thanks.html` | Intake-only confirmation (`noindex`) |

Screenshot evidence: `launch/evidence/cyb-254/` (desktop + mobile, hub/concierge/sponsor).

---

## Visual system

Uses **Dispatch** tokens from `launch/design-tokens.css` (Aurora-aligned):

| Token | Value | Use |
| --- | --- | --- |
| `--cn-signal` | `#e8ff3a` | Concierge primary CTA, featured card accent |
| `--cn-coral` | `#ff8a5c` | Sponsored primary CTA |
| `--cn-ink` / `--cn-bone` | dark/light base | Background + text |
| `--cn-serif` | Fraunces | Headlines |
| `--cn-ui` | Geist | Body + UI |

Hero mockups: `launch/assets/cybernative-concierge-hero.svg`, `cybernative-sponsor-hero.svg`.

---

## Offer cards + checkout CTAs

### Primary CTAs (CYB-6 copy — exact strings)

| Offer | Button label | `data-checkout` | GA4 event |
| --- | --- | --- | --- |
| Agent Launch Concierge | **Reserve $499 Concierge Slot** | `concierge` | `concierge_cta_click` |
| Sponsored Builder Launch | **Reserve $250 Sponsored Launch** | `sponsored` | `sponsor_cta_click` |
| Fit call (backup) | **Book fit call** / **Book 20-minute fit call** | `fit-call` | (click tracked via page context) |

### Placement

| Page | Primary checkout placement |
| --- | --- |
| Hub (`index.html`) | Offer cards `#concierge` / `#sponsor` — full-width checkout buttons |
| Concierge | Hero + pricing block — duplicate CTA for scroll depth |
| Sponsor | Hero + pricing block — duplicate CTA for scroll depth |
| Hub hero | Links to detail pages (education path); cards handle payment intent |

### Pending state (pre-Stripe)

When `checkout-config.js` still contains `REPLACE_*` placeholders, `launch.js` sets `data-checkout-pending="true"` on CTAs. CSS shows a dashed signal outline so reviewers know wiring is staged, not broken.

---

## Engineering handoff contract

### Single-file checkout wiring

**File:** `launch/checkout-config.js` — the only file CTO/CFO edits at go-live.

```javascript
window.CYBERNATIVE_CHECKOUT = {
  conciergeSlot: "https://buy.stripe.com/<live-concierge-link>",
  sponsoredSlot: "https://buy.stripe.com/<live-sponsored-link>",
  fitCall: "https://cal.com/<your-booking>",
  successUrl: "https://cybernative.ai/launch/checkout-success",
  intakeThanksUrl: "https://cybernative.ai/launch/thanks"
};
```

**HTML:** No edits required. All `[data-checkout]` anchors hydrate via `launch.js`.

**Stripe dashboard:** Set each Payment Link **After payment → Redirect** to `successUrl`.

### CTA HTML pattern (for any new buttons)

```html
<a class="button primary"
   data-checkout="concierge"
   data-event="concierge_cta_click"
   data-offer="concierge"
   href="#">Reserve $499 Concierge Slot</a>
```

### Post-payment flow

```mermaid
flowchart LR
  A[CTA click] --> B[Stripe Payment Link]
  B --> C[/launch/checkout-success]
  C --> D[Concierge or Sponsor intake form]
  D --> E[/launch/thanks]
```

1. Buyer pays via Stripe Payment Link.
2. Stripe redirects to `checkout-success.html`.
3. Buyer completes offer-specific intake (`#intake` on concierge or sponsor page).
4. Form submits to `thanks.html` (demo) or production endpoint (Tally/Typeform/HubSpot).

### Intake fields (required contract)

| Field | `name` | Concierge | Sponsor | Hub quick intake |
| --- | --- | --- | --- | --- |
| Name | `name` | ✓ | ✓ | ✓ |
| Work email | `email` | ✓ | ✓ | ✓ |
| Company | `company` | ✓ | ✓ | ✓ |
| Product URL | `product_url` | ✓ | ✓ | optional |
| Offer | `offer` | hidden | hidden | select |
| Launch category | `category` | select | select | — |
| Target launch week | `launch_week` | ✓ | ✓ | — |
| Contact channel | `contact_channel` | ✓ | ✓ | — |
| Launch summary | `launch_summary` | textarea | textarea | textarea |
| UTM passthrough | `utm_*` | hidden ×4 | hidden ×4 | hidden ×4 |

**Production:** Replace `action="./thanks.html" method="get"` with form backend. Preserve field names for CRM routing.

### UTM support

`launch.js` reads `?utm_source&utm_medium&utm_campaign&utm_content` from URL and populates hidden form fields. Outbound links from [CYB-6](/CYB/issues/CYB-6) should append UTMs, e.g.:

`https://cybernative.ai/launch/concierge?utm_source=linkedin&utm_medium=outbound&utm_campaign=cyb6-sprint`

### GA4 events (already wired in `launch.js`)

| Event | Trigger |
| --- | --- |
| `seo_landing_view` | Page load |
| `concierge_cta_click` | Concierge checkout CTA |
| `sponsor_cta_click` | Sponsor checkout CTA |
| `pricing_deposit_click` | Any `[data-offer]` link |
| `signup_start` | Form submit start |
| `lead_form_submit` | Form submit with offer/category |
| `signup_complete` | `thanks.html` / checkout-success |

Set `data-ga-measurement-id` on `<html>` at deploy.

---

## Copy alignment — CYB-6 → page slots

| CYB-6 asset | Landing slot | Status |
| --- | --- | --- |
| Concierge promise: "clean technical topic, secure agent identity angle, founder-facing feedback" | Concierge hero lede + deliverables | ✓ |
| Concierge CTA: "Reserve a $499 concierge slot" | `Reserve $499 Concierge Slot` buttons | ✓ |
| Sponsor promise: "clearly labeled sponsored launch" | Sponsor hero + trust chips | ✓ |
| Sponsor CTA: "Reserve a $250 sponsored launch slot" | `Reserve $250 Sponsored Launch` buttons | ✓ |
| Backup CTA: "Book a 20-minute launch fit call" | `#fit-call` bands on all pages | ✓ |
| Concierge includes list (5 bullets) | Concierge pricing `<ul>` | ✓ |
| Sponsor includes list (4 bullets) | Sponsor pricing `<ul>` | ✓ |
| ICP examples (MCP, agent frameworks, observability) | Sponsor "Best fit" section | ✓ |
| LinkedIn/X post offer framing | Hub hero + offer section headings | ✓ |
| Intake fields from CYB-6 handoff | All three forms | ✓ |

Full outbound copy source: `cybernative-14-day-revenue-sprint.md` in project workspace.

---

## Deploy checklist (engineering — on Stripe enablement)

1. Publish `launch/` static files to production paths (blocked on [CYB-19](/CYB/issues/CYB-19) prod deploy).
2. Replace `checkout-config.js` placeholder values (one file).
3. Wire intake forms to Tally/Typeform/HubSpot (currently demo → `thanks.html`).
4. Add "Launch an Agent" nav per `docs/cyb-208-theme-nav-spec.md`.
5. Merge `launch/sitemap.xml` routes into production sitemap.
6. Set GA4 measurement ID on `<html>`.

**Same-day ship estimate:** Steps 1–2 only if static hosting path exists; full funnel steps 1–6.

---

## What is explicitly out of scope (CYB-254)

- Live Stripe Payment Links (board path A / CYB-33)
- Production form backend
- Discourse theme nav deploy
- Outbound sending (CYB-6 blocker — CEO channel access)

---

## Review sign-off

| Gate | Status |
| --- | --- |
| Mockup pages render with brand tokens | ✓ |
| Checkout CTA contract documented | ✓ |
| CYB-6 copy mapped to slots | ✓ |
| Eng handoff = one config file | ✓ |
| Screenshot evidence in repo | ✓ `launch/evidence/cyb-254/` |
| Stripe / prod deploy | Deferred (not blocking this issue) |
