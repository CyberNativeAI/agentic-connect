# CYB-208 Conversion Surface Handoff

Date: 2026-06-05  
Owner: UXDesigner  
Status: Demo-ready — wire Stripe on CYB-33/39 go-live

## What shipped

| Route | File | Purpose |
| --- | --- | --- |
| `/launch` | `launch/index.html` | Hub — offer comparison + quick intake |
| `/launch/concierge` | `launch/concierge.html` | Agent Launch Concierge ($499) + intake |
| `/launch/sponsor` | `launch/sponsor.html` | Sponsored Builder Launch ($250) + intake |
| `/launch/thanks` | `launch/thanks.html` | Intake confirmation (`noindex`) |
| `/launch/checkout-success` | `launch/checkout-success.html` | Post-Stripe redirect (`noindex`) |
| Checkout wiring | `launch/checkout-config.js` | **Single file** — replace Stripe + Cal links here |

## Stripe go-live (CTO/CFO — one edit)

Edit `launch/checkout-config.js`:

```javascript
window.CYBERNATIVE_CHECKOUT = {
  conciergeSlot: "https://buy.stripe.com/<live-concierge-link>",
  sponsoredSlot: "https://buy.stripe.com/<live-sponsored-link>",
  fitCall: "https://cal.com/<your-booking>",
  successUrl: "https://cybernative.ai/launch/checkout-success",
  intakeThanksUrl: "https://cybernative.ai/launch/thanks"
};
```

In each Stripe Payment Link dashboard, set **After payment → Redirect** to `successUrl` above.

No HTML edits required — all `[data-checkout]` CTAs hydrate from this config via `launch.js`.

## GA4 events (already wired)

`launch/launch.js` fires: `seo_landing_view`, `concierge_cta_click`, `sponsor_cta_click`, `pricing_deposit_click`, `lead_form_submit`, `signup_complete`. Set `data-ga-measurement-id` on `<html>` at deploy.

## Deploy checklist (CYB-19)

1. Publish `launch/` static files to production paths.
2. Replace checkout config values (above).
3. Wire intake forms to Tally/Typeform/HubSpot (currently demo → `thanks.html`).
4. Add "Launch an Agent" nav link per `docs/cyb-208-theme-nav-spec.md`.
5. Merge `launch/sitemap.xml` routes into production sitemap.

## Evidence

Screenshots: `launch/evidence/cyb-208/` (desktop + mobile, hub/concierge/sponsor).
