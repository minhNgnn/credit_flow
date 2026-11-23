# SHB Design System

A design system for **SHB Bank's CRM** — the internal relationship-management application used by bankers and relationship managers to track customers, accounts, deals, and service activity. SHB's brand reputation rests on being **sustainable, safe, and efficient**; this system is built to feel calm, precise, and trustworthy rather than flashy.

## Sources

- Brand mark: `uploads/SCR-20260712-nkbl.png` (provided by the user) — the only ground-truth brand asset available this run. Colors, no other brand guidelines, codebase, or Figma file were provided.
- No codebase, Figma file, or existing product screens were attached. **This system was built from scratch**, seeded only by the logo and the one-paragraph company description above. If a codebase or Figma file exists for the real SHB CRM, attach it and this system should be revised to match it exactly — right now the components, screens, and copy are informed guesses in the brand's likely visual language, not a recreation of a real product.

## Substitutions & flags — please review

- **Fonts are a Google Fonts substitution, not real SHB brand fonts.** The logo's wordmark has rounded, geometric curves; the closest freely-available match is **Poppins** (display/headlines) paired with **Inter** (body/UI) and **JetBrains Mono** (account numbers, IDs). If SHB has real brand font files, please share them and I'll swap `tokens/typography.css`.
- **Colors were extracted directly from the uploaded logo** via pixel sampling: navy `#2F2E79` and orange `#F37021`. These are the two most-confident tokens in the system.
- **No icon set was provided.** Iconography in components/screens uses small hand-drawn-in-code SVG glyphs (arrows, bell, etc.) as placeholders only where unavoidable — see Iconography section. If SHB uses a specific icon library (Lucide, Phosphor, a custom set), tell me and I'll swap every instance.
- **No existing UI or codebase was provided**, so the CRM screens in `ui_kits/crm/` are an original, brand-appropriate interpretation — not a recreation of a real product. Treat them as a starting proposal, not ground truth.

## Content fundamentals

- **Voice:** professional, plain-spoken, reassuring. Short declarative sentences. No hype, no exclamation points, no forced friendliness.
- **Point of view:** second person for UI copy directed at the banker ("You have 3 deals closing this week"); first person plural for the product's own voice in empty states and confirmations ("We'll notify you when this clears").
- **Casing:** sentence case everywhere — headings, buttons, labels, nav items. Never title case, never all-caps except tiny metadata labels (e.g. table column headers at 12px).
- **Numbers & money:** always show currency with symbol and thousands separators ($128,400.00); dates as "Jul 12, 2026", never relative-only ("3 days ago") for anything financial.
- **Emoji:** none. This is a regulated banking context — emoji would undercut trust.
- **Tone examples:**
  - Button: "Send statement" (not "Send statement now!" or "SEND STATEMENT")
  - Empty state: "No deals yet. Add one to start tracking this relationship."
  - Error: "We couldn't verify this account number. Double-check and try again."
  - Confirmation: "Statement sent to client."
- **Vibe:** measured, competent, quietly confident — a private banker, not a fintech startup.

## Visual foundations

- **Color:** Orange (`--color-orange-600`, sampled from the logo, matching shb.com.vn's primary CTAs/links/tab-underlines) is the primary brand color — used for primary buttons, links, active-tab indicators, and key highlights. Navy (`--color-navy-700`, also sampled from the logo) is the secondary/structural color — used for the sidebar and header surfaces, headings, and a secondary button variant. Neutrals are a cool gray tinted slightly toward navy, never pure gray. Semantic colors (success/warning/danger/info) are desaturated relative to the brand colors so status never competes visually with navy/orange.
- **Type:** Poppins (display, 600–800 weight) for headings and hero numbers; Inter (400–600) for all UI and body text; JetBrains Mono for account numbers, reference codes, IDs. Type is set tight (`tracking-tight` on headings) to read as precise rather than soft.
- **Spacing:** 4px base unit, scale from 4 to 96px. Cards use 24px internal padding by default; tight variants use 16px.
- **Backgrounds:** flat surfaces only — no gradients, no photography, no illustration, no texture/grain. The page background is a very light cool gray (`--surface-page`); cards are white. The one "full-bleed" surface is the inverse navy block used for the app's left rail / header — a solid fill, not a gradient.
- **Animation:** minimal and utilitarian. State transitions (hover, focus, toggle) use `--duration-fast` (120ms) to `--duration-base` (180ms) with a standard ease-out curve — no springs, no bounce, no overshoot. Nothing animates just for decoration.
- **Hover states:** buttons and brand-colored surfaces darken one step (`--brand-primary-hover`, `--brand-accent-hover`); neutral/secondary surfaces go to `--surface-sunken`. No opacity-based hovers on solid-fill elements.
- **Press states:** buttons scale to 0.98 on press — a small, quiet confirmation, no color change beyond the existing hover state.
- **Borders:** 1px `--border-subtle`/`--border-default` hairlines throughout; a 1.5px `--border-focus` (navy) ring plus a soft `--shadow-focus` halo on keyboard focus — no bright blue browser-default outlines.
- **Shadows:** a restrained 4-step elevation scale (`--shadow-xs` through `--shadow-lg`), all navy-tinted rather than pure black, used to lift cards and modals only — flat elements (badges, inline chips) never carry shadow.
- **Radius:** 4/8/12/16px scale. Buttons and inputs use 8px; cards and dialogs use 12–16px; pills (badges, switch track) are fully rounded.
- **Cards:** white fill, 1px `--border-subtle` outline, `--shadow-sm`, 12px radius, 24px padding. No colored left-border accent strips.
- **Transparency/blur:** the only use is the modal overlay scrim (`--surface-overlay`, translucent navy) behind dialogs — no frosted-glass/backdrop-blur anywhere else.
- **Imagery:** none provided; none invented. If/when product photography exists, it should read neutral-cool (no warm filters) to match the navy-forward palette — avoid this until real assets are supplied.

## Iconography

No icon library or icon font was provided with the brand assets. Do not invent an icon system wholesale — for this build, a minimal set of inline SVG glyphs (arrows, search, bell, close, checkmark) was hand-drawn only where a component genuinely needed one (e.g. Checkbox's checkmark, Dialog's close). These are intentionally plain single-path glyphs, not a styled icon set, and are marked as placeholders. **If SHB has a real icon library (Lucide, Phosphor, custom SVG set, icon font), share it and every placeholder glyph in this system should be swapped for the real set.** No emoji, no Unicode symbol icons are used anywhere in the system, consistent with the "no emoji" content rule above.

## Intentional additions

No component inventory was provided by a source (no codebase/Figma), so a standard set was authored from scratch per the design-system brief: Button, IconButton, Card, Badge (`components/core`, `components/feedback`), Input, Select, Checkbox, Radio, Switch (`components/forms`), Tabs (`components/navigation`), Tooltip, Toast, Dialog (`components/feedback`). All are "intentional additions" in the sense that the whole set was invented for a from-scratch brand, not that any one deviates from a source.

## Components

- **Core** (`components/core/`): `Button` (5 variants × 3 sizes), `Card`, `IconButton` (ghost/solid/outline)
- **Forms** (`components/forms/`): `Input`, `Select`, `Checkbox`, `Radio`, `Switch`
- **Navigation** (`components/navigation/`): `Tabs`
- **Feedback** (`components/feedback/`): `Badge`, `Tooltip`, `Toast`, `Dialog`

## Index

- `styles.css` — root stylesheet, imports everything under `tokens/`
- `tokens/` — `colors.css`, `typography.css`, `spacing.css`, `effects.css` (radius/shadow/motion), `base.css` (resets)
- `guidelines/` — foundation specimen cards (Colors, Type, Spacing, Brand groups in the Design System tab)
- `assets/logo/` — SHB logo, as uploaded
- `components/` — reusable primitives, grouped as above
- `ui_kits/crm/` — CRM product screens: login, dashboard, customer profile, deal pipeline
- `SKILL.md` — Claude Code–compatible skill definition for this design system
