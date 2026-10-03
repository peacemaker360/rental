---
name: Rental Desk
description: Compact operational UI for music-association instrument rentals
colors:
  accent: "#0b6b5d"
  accent-strong: "#094d43"
  background: "#f6f7f3"
  panel: "#ffffff"
  panel-soft: "#eef5ef"
  ink: "#1e2528"
  muted: "#617071"
  line: "#d8dfda"
  warning: "#b55d13"
  danger: "#b3261e"
  information: "#22577a"
  navigation: "#1f302e"
  navigation-ink: "#f8fbf8"
---

## Overview

Established 2026-10-03 for [PRODUCT.md](PRODUCT.md). Tokens are extracted from
`public/styles.css`. This captures incumbent design and interaction requirements,
not a completed visual/accessibility audit. Owner confirmation of visual direction
is pending; no redesign is authorized by this document alone.

Prioritize scanning, repeated actions, and confidence in state. This is a CRUD
workspace, not a marketing page. The basic member portal is a complete simple
experience, not an admin dashboard with controls removed.

## Colors

Use green for primary commands/selection, light neutral record surfaces, and
dark green navigation. Keep distinct warning, danger, and information colors;
do not make every state green. Orange means attention/due soon, red overdue/error,
and blue information. Pair color with labels, dates, or recognizable icons.
Do not use severity colors just to distinguish arbitrary roles.

Light flyouts use panel/ink colors even inside dark navigation. Never inherit
white sidebar text into white cards. Verify actual contrast combinations.

## Typography

Use the existing Inter/system sans-serif stack; external font loading must not
be required for usability. Strong record names, readable body text, quieter
metadata, and modest tool-sized headings establish hierarchy.
Use fixed type steps rather than viewport-width scaling and zero letter spacing.
Wrap long names/emails/German labels without pushing controls outside the viewport.
Do not truncate the only readable copy of critical dates, roles, or references.

## Layout

Desktop uses a 248px sidebar and `minmax(0, 1fr)` content track. CSS adapts at
960px and 680px; inspect the full cascade. Preserve desktop split-view details.
Keep search/filter/sort near the list heading. Wide tables may scroll inside a
container; the page must not overflow horizontally.

Sections are unframed layouts/full-width bands. Cards belong to repeated entities,
personal rentals, and bounded tools, not nested page-section containers. Keep
toolbars, counters, icons, and journey markers dimensionally stable.

Mobile requirements:
- One minimal sticky identity/header with account access and a menu toggle.
- Expanded navigation must not duplicate the logo or stay screen-filling.
- Wrap/collapse menus; no sideways scrolling to discover destinations.
- Selected details open directly beneath the row/card using desktop detail
  content; hide the duplicate bottom panel.
- Compact import/export icons sit beside the heading. Hitobito is Members-only.
- Back-to-top floats clear of forms/dialogs and device safe areas.
- Prefer 44px mobile icon targets; test German text, long lists, and zoom/reflow.

## Elevation & Depth

Use borders/spacing for routine grouping and stronger shadows for floating
surfaces, not every section. The existing shadow is
`0 18px 50px rgba(24, 37, 34, 0.12)`.
Account flyouts open upward from lower/sidebar anchors where space permits,
adapt to available space, and never clip. Close on outside interaction, focus
leaving the surface, or Escape; restore keyboard focus appropriately. The user
icon must not be the only dismissal mechanism.

## Shapes

Use restrained rectangular panels/controls. Standard/new cards and controls
have radii no larger than 8px; incumbent exceptions do not justify rounding
everything. Circular shapes fit journey stops and familiar iconography.
Use selects for roles/member choices, toggles/checkboxes for binary settings,
date inputs for dates, and recognizable command buttons.

## Components

### Shell And Account

Association identity is context, not a browser-side permission grant. Offer
switching only when an authorized choice exists; Clerk owns hosted organization
selection. Keep revision/update metadata in operational/admin views, not the
member portal. Never expose legacy debug privileges in hosted UI.
Provide a recognizable user icon, identity/role/profile, explicit sign-in/out,
and account settings. Show member help only when association contact exists.

### Lists And Forms

Rows have visible selection and keyboard-operable detail access; closing detail
preserves useful list context. Embedded controls must not accidentally open rows.
Nullable dates are clearable. Represent a stored email hash as "configured", not
an email; replacement is deliberate. Failed saves retain input, errors are
visible, and repeat submissions are disabled while pending.

### Journeys

Use connected labeled stops for rental/service events, dates, conditions, and
job notes. This is operational history, not decoration. Align dates with phases
and keep marker baselines aligned even when dates are absent. Planned phases
must not imply completed events.
Rental cards show instrument, state, start, due, and return. Missing due means
localized "Forever". Current due-soon threshold: 31 days inclusive; due today
is warning, past due is overdue, and returned loans have no active overdue warning.

### Loading And Feedback

Use restrained shimmer/skeleton/loading treatment while waiting; never flash a
false empty dataset. Respect reduced motion and retain a static loading signal.
Banners exist only for messages, last up to one minute, and have close controls.
Pending requests and unresolved errors need persistent content, not only timers.
Demo loading is onboarding-only and hidden once working data exists. Replacement
imports/destructive actions require contextual confirmation.

### Authentication And Admissions

Distinguish signed out, checking, pending session task, missing membership,
pending request, unmapped organization, and provider/network failure. De-emphasize
irrelevant phases without illegibility. Cookie presence is not verified sign-in.
Retain retry/check-access and session-aware sign-out. A join form must not pretend
to repair an unmapped organization. Code input starts empty with a hint; submit
needs a nonblank code and valid identity. Prefill verified email when available.
Show submitted state, reference, association, and configured contact. Distinguish
submission from notification delivery and approval. Browser-saved status is not
live approval evidence. Named Clerk admin handoffs are intentional exceptions to
provider-neutral general sign-in copy.

### Accessibility And Localization

Acceptance targets keyboard operation, visible focus, semantic labels, named icon
buttons, status announcements, and WCAG 2.2 AA contrast/reflow. No certification
is claimed. Tooltips supplement accessible names. Prefer an existing icon library
for new controls. Update EN/DE together, including errors, empty states, tooltips,
and dates; do not rely on English widths or concatenate translated sentence parts.

## Do's and Don'ts

- Preserve compact CRUD and distinct member/admin experiences.
- Verify desktop/mobile with long German labels, absent dates, long lists,
  flyouts, reduced motion, keyboard interaction, and failed requests.
- Use actual instrument information and purposeful imagery where identification
  benefits; invented fixtures/images are not evidence of real inventory.
- Avoid marketing heroes, decorative gradients/orbs, oversized headings, and
  nested cards. Loading shimmer is functional, not the visual theme.
- Never clip flyouts, bury mobile details under long lists, duplicate identity
  headers, or require sideways menu scrolling.
- Hiding controls is not authorization; backend enforcement remains mandatory.

These are implementation/review standards, not a claim that current screens
already satisfy every item. This documentation change does not redesign the app.
