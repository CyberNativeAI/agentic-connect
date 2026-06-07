# CYB-999196 — Launch surface QA report

Date: 2026-06-06  
Agent: UXDesigner  
Scope: `launch/index.html`, `launch/concierge.html`, `launch/sponsor.html`

## Method

- Local static server + Playwright full-page captures at 1440×900 (desktop) and 390×844 (mobile).
- Before evidence: `launch/evidence/cyb-999196-before/`
- After evidence: `launch/evidence/cyb-999196-after/`

## What looks good

| Area | Finding |
| --- | --- |
| First-screen clarity | Headlines state offer + audience (builders, MCP, devtools) without fluff. |
| CTA hierarchy (offer cards) | Signal/coral full-width checkout buttons dominate; ghost secondary links are clearly subordinate. |
| Contrast | Bone on ink + signal/coral CTAs meet readable contrast on dark Dispatch tokens. |
| Product inspectability | Deliverables, pricing bullets, fit/not-fit lists, and intake fields make scope concrete. |
| Pending checkout | Dashed outline on `[data-checkout-pending]` correctly signals staged Stripe wiring. |

## Fixes applied this heartbeat

1. **Hub hero CTA hierarchy** — demoted fit call from competing ghost button to inline text link under primary offer buttons (`index.html`, `landing.css`).
2. **Buyer-facing copy** — replaced internal engineering notes on concierge/sponsor pricing blocks and intake footers with reassurance copy buyers can act on.
3. **Mobile nav** — wrapped nav links instead of horizontal scroll at ≤680px (`landing.css`).

## Remaining punch-list (not fixed — needs eng/board)

1. **Live deploy + Stripe** — checkout CTAs still pending until `checkout-config.js` placeholders are replaced ([CYB-33](/CYB/issues/CYB-33)); cannot verify live conversion path until prod deploy ([CYB-19](/CYB/issues/CYB-19)).
2. **Hub hero → checkout path** — hero buttons route to detail pages (by spec); consider adding price-anchored checkout buttons above the fold on hub once Stripe is live so buyers can pay without an extra click.
3. **Form backend** — intake forms still demo to `thanks.html`; wire to Tally/Typeform/HubSpot before outbound campaigns.

## Verdict

Conversion surfaces are **deploy-ready for design review**. Copy no longer leaks internal wiring. Safe CSS/HTML polish committed with screenshot evidence.
