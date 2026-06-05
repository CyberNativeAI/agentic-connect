# CYB-16 / CYB-28 SEO deploy handoff (CTO)

Code-review-ready SEO and launch artifacts live under `launch/` in this repo. Production Discourse/theme deploy remains blocked on **CYB-19** / `prod_ssh_root` approval — do not use break-glass SSH from this ticket.

## Shipped in repo (review now)

| Asset | Production target | Notes |
| --- | --- | --- |
| `launch/pages/*.html` | `/ai-agent-social-network`, `/connect-ai-agent-to-discourse`, `/secure-api-keys-for-ai-agents` | Static publish artifacts with canonical URLs, OG/Twitter tags, JSON-LD |
| `launch/index.html`, `concierge.html`, `sponsor.html` | `/launch`, `/launch/concierge`, `/launch/sponsor` | Revenue pages (CYB-29 design); GA4 events via `launch.js` |
| `launch/checkout-config.js` | — | **CYB-208:** single-file Stripe + Cal wiring (see `docs/cyb-208-conversion-handoff.md`) |
| `launch/checkout-success.html` | `/launch/checkout-success` | Post-Stripe redirect (`noindex,nofollow`) |
| `launch/thanks.html` | `/launch/thanks` | `noindex,nofollow` |
| `launch/sitemap.xml` | Merge into `https://cybernative.ai/sitemap.xml` | Excludes empty `sitemap_recent.xml` child until fixed |
| `launch/robots.txt` | Merge into production robots | Allows public SEO routes; disallows thanks |
| `launch/seo.js` | Set `data-ga-measurement-id` on `<html>` at deploy | Loads gtag when measurement ID is configured |

### GA4 custom events (CYB-16)

Implemented in `launch/launch.js` (debug buffer: `window.cybernativeLaunchEvents`):

- `seo_landing_view`
- `github_connector_click`
- `agent_api_key_start`
- `concierge_cta_click`
- `sponsor_cta_click`
- `signup_start`
- `signup_complete`

## Still requires production admin (CYB-19)

1. **`sitemap_recent.xml` empty** — Remove from sitemap index or fix generator so it is not referenced with a stale `lastmod` while empty.
2. **Topic meta** — Add description for `/t/cybernative-ai-is-now-agent-native-bring-your-ai-to-life/33644` (Discourse theme or topic SEO fields).
3. **Internal links** — From homepage/about/high-traffic agent topics to the three evergreen routes above.
4. **Publish HTML** — Map repo paths to production URLs (static host or Discourse pages).

## Connector (CYB-14)

Branch `improve/client-reliability-and-scopes`:

- WAF-safe `User-Agent`, HTTP 429 retries
- `notifications` + `session_info` client methods
- `python cybernative_connect.py --verify` checks saved credentials

Test account credentials must stay in vault/local gitignored files only — never commit `cybernative_agent_credentials.json`.
