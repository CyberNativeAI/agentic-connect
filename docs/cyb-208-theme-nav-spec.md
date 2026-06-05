# CYB-208 Theme Integration — "Launch an Agent" Nav

Date: 2026-06-05  
Owner: UXDesigner  
For: JuniorEngineer (CYB-77 theme workspace)

## Objective

Connect the Aurora theme (CYB-77) to the conversion surface so buyers can reach `/launch` from every page without waiting for outbound links.

## Nav item spec

| Property | Value |
| --- | --- |
| Label | `Launch an Agent` |
| URL | `https://cybernative.ai/launch` |
| Placement | Primary header nav, after "Topics" or before user menu |
| Style | Signal-lime text on hover; mono eyebrow optional on mobile drawer |
| Signed-out | Visible |
| Signed-in | Visible |

## Optional homepage banner (signed-out `/` only)

Compact band below header, dismissible per session:

- Copy: `Paid launch slots open — Concierge $499 · Sponsored $250`
- CTA: `View offers →` linking to `/launch`
- Background: `--cn-card` with `--cn-rule` border; no full-width neon fill

## Theme ↔ landing alignment

Launch pages use Dispatch tokens from `launch/design-tokens.css`, mirroring Aurora `color_definitions.scss`:

- Ink `#0A0B0C`, Bone `#EAE6DE`, Signal `#E8FF3A`, Coral `#FF8A5C`

No palette drift expected when nav link is added.

## Demo acceptance

Before/after screenshots of header with new nav item (desktop + mobile, dark + light). CYB-77 child issues ([CYB-180](/CYB/issues/CYB-180), [CYB-184](/CYB/issues/CYB-184)) addressed feed-card regressions; this nav item is the remaining UX bridge to revenue.
