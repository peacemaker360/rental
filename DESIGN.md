---
name: Rental Desk
description: A calm bilingual operations ledger for association instrument rentals
colors:
  canvas: "#f6f7f3"
  surface: "#ffffff"
  surface-soft: "#eef5ef"
  ink: "#1e2528"
  muted-ink: "#617071"
  divider: "#d8dfda"
  association-green: "#0b6b5d"
  association-green-deep: "#094d43"
  sidebar-green: "#1f302e"
  warning-amber: "#b55d13"
  danger-red: "#b3261e"
  information-blue: "#22577a"
typography:
  headline:
    fontFamily: "Aptos, Segoe UI Variable, Segoe UI, ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(1.8rem, 3vw, 2.6rem)"
    fontWeight: 700
    lineHeight: 1.2
  title:
    fontFamily: "Aptos, Segoe UI Variable, Segoe UI, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.2rem"
    fontWeight: 700
    lineHeight: 1.3
  body:
    fontFamily: "Aptos, Segoe UI Variable, Segoe UI, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Aptos, Segoe UI Variable, Segoe UI, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.78rem"
    fontWeight: 700
    lineHeight: 1.4
rounded:
  control: "8px"
  segmented: "6px"
  pill: "999px"
spacing:
  xs: "6px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  section: "28px"
components:
  button-primary:
    backgroundColor: "{colors.association-green}"
    textColor: "{colors.surface}"
    rounded: "{rounded.control}"
    height: "42px"
  button-ghost:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    height: "42px"
  navigation-active:
    backgroundColor: "#314743"
    textColor: "{colors.surface}"
    rounded: "{rounded.control}"
    height: "42px"
---

# Design System: Rental Desk

## Overview

**Creative North Star: "Association Ledger"**

Rental Desk feels like a carefully maintained shared record: calm, accountable, and immediately usable. Its dark green frame gives the application institutional steadiness, while warm off-white work surfaces and restrained teal actions keep long operational sessions comfortable. The visual language is compact enough for data work without becoming cramped.

Expression comes from precision rather than decoration. Repeated eight-pixel corners, clear status colors, firm labels, and consistent surface boundaries make changing rental data feel safe. The interface should remain equally legible for staff working across dense tables and members checking a small set of personal rentals.

**Key Characteristics:**

- Deep green navigation frame around pale working surfaces
- Compact, predictable controls and data-dense layouts
- Restrained accent color reserved for actions and focus
- Clear semantic status treatments
- Responsive behavior that preserves task order and readability

## Colors

The palette combines ledger-paper neutrals with deep association greens and a small set of semantic status colors.

### Primary

- **Association Green:** Primary actions, links, focus cues, and selected operational emphasis.
- **Deep Association Green:** Hover and pressed emphasis for primary actions.
- **Sidebar Green:** Persistent navigation frame and the strongest brand field.

### Secondary

- **Information Blue:** Rented and informational states that need distinction from actions.
- **Warning Amber:** Due dates, attention states, and cautionary operational signals.
- **Danger Red:** Destructive controls and errors only.

### Neutral

- **Ledger Canvas:** Page background that softens contrast around white work surfaces.
- **Paper Surface:** Cards, tables, dialogs, menus, and controls.
- **Soft Green Surface:** Quiet grouping, notices, and selected rows.
- **Charcoal Ink:** Primary text.
- **Muted Ink:** Supporting text and labels.
- **Divider:** Borders and separators that organize data without dominating it.

**The Reserved Accent Rule.** Association Green marks action, selection, or focus; it does not become broad decoration inside the workspace.

**The Semantic Color Rule.** Warning, danger, and information colors keep stable meanings across English and German views.

## Typography

**Display Font:** Aptos with Segoe UI Variable and system sans-serif fallbacks
**Body Font:** Aptos with Segoe UI Variable and system sans-serif fallbacks

**Character:** Neutral, sturdy, and highly readable. Weight and size establish hierarchy while the single family keeps mixed data, controls, and bilingual copy visually coherent.

### Hierarchy

- **Headline** (700, `clamp(1.8rem, 3vw, 2.6rem)`, 1.2): Current view titles and the strongest page orientation.
- **Title** (700, `1.2rem`, 1.3): Panel and dialog headings.
- **Body** (400, `1rem`, 1.5): Operational copy, record values, and form content.
- **Label** (700, `0.78rem`, 1.4, uppercase where used): Field names, metadata, and compact navigational context.

**The Plain Language Rule.** Type supports scanning and comprehension; decorative type treatments do not compete with records or actions.

## Layout

Desktop uses a fixed 248-pixel sidebar and a flexible workspace. The workspace carries a top bar, messages, and a view region with generous outer padding, while panels, statistics, toolbars, and tables use an eight-pixel rhythm with 12-, 16-, 24-, and 28-pixel grouping intervals. Dense information stays aligned to shared grid and table edges.

At narrow widths the persistent sidebar yields to a mobile app bar and menu flow. Toolbars and action groups wrap, tables retain horizontal scrolling when their data cannot collapse safely, and primary actions remain reachable. Responsive changes preserve task sequence rather than merely shrinking the desktop composition.

**The Operational Order Rule.** Navigation, context, action, feedback, and records appear in that order at every viewport size.

## Elevation & Depth

The system is flat by default and separates regions with tonal surfaces and fine borders. A single soft ambient shadow (`0 18px 50px rgba(24, 37, 34, 0.12)`) is reserved for overlays, menus, and loading surfaces that must visibly float above the ledger.

**The Earned Elevation Rule.** A surface receives a shadow only when it temporarily sits above the main workflow.

## Shapes

Eight-pixel corners unify controls, panels, dialogs, and branded marks. Six-pixel corners distinguish nested segmented controls, while fully rounded pills are reserved for compact statuses and small identity indicators. Borders are thin and quiet; silhouettes stay rectilinear and space-efficient.

**The One Radius Rule.** Use the eight-pixel control radius unless the element is explicitly nested or semantically a pill.

## Components

### Buttons

- **Shape:** Compact rectangular controls with gently rounded corners (8px) and a minimum touch-friendly height near 42px.
- **Primary:** Association Green with white text; used for the single leading action in a task context.
- **Ghost:** White or transparent with a Divider border; used for utilities and secondary actions.
- **Danger:** Pale red surface with a restrained red border and text; used only for destructive actions.
- **Hover / Focus:** Primary actions deepen in color; all controls retain a clear visible focus treatment.

### Navigation

- **Style:** Text-first rows inside the Sidebar Green frame, with a darker lifted green selection field and white active text.
- **Behavior:** Selected state is obvious without relying on color alone through the filled row treatment.

### Cards / Containers

- **Corner Style:** Eight-pixel corners with Divider borders.
- **Surface:** Paper Surface for data containers; Soft Green Surface for contextual emphasis.
- **Depth:** Flat at rest. Menus and modal layers may use the ambient shadow.

### Inputs

- **Style:** White fields with a Divider border, dark text, and the shared control radius.
- **Labels:** Compact, firm labels above fields; supporting and error copy remains adjacent to the affected control.

### Status Pills

- **Style:** Fully rounded compact labels with tinted backgrounds and dark semantic text.
- **State:** Green indicates available or returned, blue indicates rented or active, amber indicates paused or attention, and red indicates overdue or destructive risk.

## Do's and Don'ts

### Do

- Keep primary actions scarce and visually decisive.
- Preserve equivalent hierarchy and meaning in English and German.
- Use borders, alignment, and spacing to organize dense records.
- Keep member views simpler while retaining the same visual system.
- Maintain keyboard focus, semantic status, and responsive reading order.

### Don't

- Add decorative gradients, glass effects, or ornamental imagery to operational views.
- Use status colors for unrelated decoration.
- Introduce new corner radii when an existing role fits.
- Hide critical rental state behind hover-only interactions.
- Compress controls or copy until German labels wrap unpredictably.
