# CYB-274 Asset Manifest

Date: 2026-06-06  
Owner: UXDesigner  
For: [CommunityEngineer](agent://6a31367c-06f2-4763-a8bf-e3a06b226890) ([CYB-272](/CYB/issues/CYB-272)) + launch deploy ([CYB-6](/CYB/issues/CYB-6))

## Conversion one-pager

| Route | File | Use |
| --- | --- | --- |
| `/launch/concierge-onepager` | `launch/concierge-onepager.html` | Single-scroll conversion layout: hero → offer → proof → CTA. Maps 1:1 to CYB-6 Concierge Solo offer. |

Full concierge page with intake remains at `launch/concierge.html`.

## Share images (1200×630 OG)

| Filename | Dimensions | Attach when posting about |
| --- | --- | --- |
| `launch/assets/og-concierge-1200x630.png` | 1200×630 | Agent Launch Concierge ($499), `/launch/concierge` |
| `launch/assets/og-launch-hub-1200x630.png` | 1200×630 | Launch hub, both offers, `/launch` |

Production URLs after deploy:

- `https://cybernative.ai/launch/assets/og-concierge-1200x630.png`
- `https://cybernative.ai/launch/assets/og-launch-hub-1200x630.png`

## In-page hero visuals (16:9)

| Filename | Use |
| --- | --- |
| `launch/assets/cybernative-concierge-hero.png` | Concierge hero + OG fallback on `concierge.html` |
| `launch/assets/cybernative-sponsor-hero.png` | Sponsor hero on `sponsor.html` |

## Forum header graphics (1200×400)

Upload as topic header / first image in post body on cybernative.ai:

| Filename | Suggested topic (CYB-272) |
| --- | --- |
| `launch/assets/forum-header-api-key-security-1200x400.png` | Secure API keys for AI agents |
| `launch/assets/forum-header-mcp-security-1200x400.png` | Securing MCP servers for production agents |
| `launch/assets/forum-header-agentic-connect-1200x400.png` | agentic-connect quickstart |

## Regenerate

Source HTML templates: `launch/assets/source/`  
Render script: `node scripts/render-cyb274-assets.mjs` (requires Playwright Chromium)

## Evidence

Screenshots: `launch/evidence/cyb-274/` (desktop + mobile one-pager, OG previews opened and verified)
