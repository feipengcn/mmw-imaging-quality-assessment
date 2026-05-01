---
version: beta
name: mmWave Imaging Operations Dashboard
description: A restrained scientific dashboard for reviewing millimeter-wave human imaging quality, balancing analytical density with clinical clarity.
colors:
  background: "#F4F6F8"
  surface: "#FFFFFF"
  surface-subtle: "#FCFCFD"
  surface-muted: "#F9FAFB"
  surface-accent: "#F7FBFF"
  surface-tint: "#F8FAFC"
  image-stage: "#101828"
  text-primary: "#172033"
  text-secondary: "#344054"
  text-muted: "#667085"
  text-soft: "#475467"
  border: "#D8DDE6"
  border-strong: "#C8D0DC"
  border-soft: "#EAECF0"
  border-accent: "#8AA2C8"
  primary: "#1F6FEB"
  primary-strong: "#1D4ED8"
  primary-soft: "#EDF4FF"
  primary-border: "#93B4E8"
  success: "#147D64"
  success-strong: "#027A48"
  success-soft: "#ECFDF3"
  success-border: "#98F5E1"
  teal-chart-fill: "#14B8A6"
  teal-chart-stroke: "#0F766E"
  teal-chart-highlight: "#5EEAD4"
  warning: "#A16207"
  warning-strong: "#B54708"
  warning-soft: "#FFFBEB"
  warning-border: "#FACC15"
  danger: "#B42318"
  danger-soft: "#FEF3F2"
  danger-border: "#FDA29B"
  tooltip-background: "#172033"
  tooltip-text: "#F8FAFC"
  white: "#FFFFFF"
typography:
  headline-lg:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: 22px
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: 0em
  headline-md:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: 16px
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: 0em
  title-sm:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: 15px
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: 0em
  body-lg:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: 0em
  body-md:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: 13px
    fontWeight: 400
    lineHeight: 1.45
    letterSpacing: 0em
  label-lg:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: 14px
    fontWeight: 700
    lineHeight: 1.35
    letterSpacing: 0em
  label-md:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: 13px
    fontWeight: 700
    lineHeight: 1.35
    letterSpacing: 0em
  label-sm:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: 12px
    fontWeight: 700
    lineHeight: 1.35
    letterSpacing: 0em
  data-lg:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: 30px
    fontWeight: 700
    lineHeight: 1
    letterSpacing: 0em
  data-md:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: 24px
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: 0em
  data-sm:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: 12px
    fontWeight: 800
    lineHeight: 1.2
    letterSpacing: 0em
rounded:
  none: 0px
  xs: 6px
  sm: 8px
  md: 10px
  lg: 12px
  pill: 999px
  full: 9999px
spacing:
  xxs: 4px
  xs: 6px
  sm: 8px
  md: 10px
  lg: 12px
  xl: 14px
  2xl: 16px
  3xl: 18px
  4xl: 20px
  5xl: 24px
  6xl: 32px
  7xl: 38px
  sidebar-width: 380px
  topbar-height: 76px
  preview-stage-min-height: 460px
  ranking-tile-image-height: 132px
elevation:
  flat: 0
  border-first: 1
  focus-ring: 2
  floating-action: 3
shadows:
  subtle: "0 1px 2px rgba(16, 24, 40, 0.12)"
  focus: "0 0 0 2px rgba(31, 111, 235, 0.16)"
  focus-strong: "0 0 0 2px rgba(31, 111, 235, 0.18)"
  floating: "0 4px 12px rgba(16, 24, 40, 0.16)"
  radar: "0 3px 6px rgba(16, 24, 40, 0.28)"
motion:
  duration-fast: 120ms
  duration-base: 240ms
  duration-spin: 900ms
  easing-standard: "ease"
  easing-linear: "linear"
components:
  app-shell:
    backgroundColor: "{colors.background}"
    textColor: "{colors.text-primary}"
    typography: "{typography.body-lg}"
  topbar:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-primary}"
    borderColor: "{colors.border}"
    padding: "{spacing.5xl}"
    height: "{spacing.topbar-height}"
  side-panel:
    backgroundColor: "{colors.surface}"
    borderColor: "{colors.border}"
    padding: 20px
    width: "{spacing.sidebar-width}"
  panel-card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.sm}"
    padding: "{spacing.2xl}"
    borderColor: "{colors.border}"
  panel-card-subtle:
    backgroundColor: "{colors.surface-subtle}"
    rounded: "{rounded.sm}"
    padding: 12px
    borderColor: "{colors.border}"
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.white}"
    typography: "{typography.label-md}"
    rounded: "{rounded.sm}"
    height: 38px
    padding: 12px
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.primary}"
    typography: "{typography.label-md}"
    rounded: "{rounded.sm}"
    height: 38px
    padding: 12px
    borderColor: "{colors.primary-border}"
  button-toolbar:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-primary}"
    typography: "{typography.label-md}"
    rounded: "{rounded.sm}"
    height: 38px
    padding: 10px
    borderColor: "{colors.border-strong}"
  segmented-control:
    backgroundColor: "#F2F4F7"
    rounded: "{rounded.sm}"
    padding: "{spacing.xxs}"
    borderColor: "{colors.border-strong}"
  segmented-control-active:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.primary}"
    rounded: 6px
  dropzone:
    backgroundColor: "{colors.surface-accent}"
    textColor: "#375A8C"
    rounded: "{rounded.sm}"
    borderColor: "{colors.border-accent}"
    height: 116px
  summary-tile:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.sm}"
    padding: 14px
    borderColor: "{colors.border}"
  image-stage:
    backgroundColor: "{colors.image-stage}"
    rounded: "{rounded.sm}"
    borderColor: "{colors.border}"
    height: "{spacing.preview-stage-min-height}"
  image-ranking-tile:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.sm}"
    padding: "{spacing.sm}"
    borderColor: "{colors.border}"
  image-ranking-tile-active:
    backgroundColor: "{colors.surface}"
    borderColor: "{colors.primary}"
    shadow: "{shadows.focus}"
  status-chip:
    backgroundColor: "{colors.surface-tint}"
    textColor: "{colors.text-secondary}"
    typography: "{typography.data-sm}"
    rounded: "{rounded.pill}"
    height: 28px
    padding: 10px
    borderColor: "{colors.border}"
  status-chip-success:
    backgroundColor: "{colors.success-soft}"
    textColor: "{colors.success-strong}"
    borderColor: "{colors.success-border}"
  status-chip-warning:
    backgroundColor: "{colors.warning-soft}"
    textColor: "{colors.warning}"
    borderColor: "{colors.warning-border}"
  status-chip-danger:
    backgroundColor: "{colors.danger-soft}"
    textColor: "{colors.danger}"
    borderColor: "{colors.danger-border}"
  tooltip:
    backgroundColor: "rgba(23, 32, 51, 0.96)"
    textColor: "{colors.tooltip-text}"
    typography: "{typography.body-md}"
    rounded: "{rounded.sm}"
    padding: 12px
    width: 240px
  radar-chart-card:
    backgroundColor: "{colors.surface-subtle}"
    rounded: "{rounded.sm}"
    padding: "{spacing.md}"
    borderColor: "{colors.border}"
  histogram-card:
    backgroundColor: "{colors.surface-muted}"
    rounded: "{rounded.sm}"
    padding: "{spacing.md}"
    borderColor: "{colors.border}"
  metric-group:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.sm}"
    borderColor: "{colors.border}"
  metric-group-header:
    backgroundColor: "{colors.surface-tint}"
    textColor: "{colors.text-primary}"
    padding: 12px
    borderColor: "{colors.border-soft}"
  list-row-active:
    backgroundColor: "{colors.primary-soft}"
    textColor: "{colors.text-primary}"
  danger-fab:
    backgroundColor: "rgba(255, 255, 255, 0.96)"
    textColor: "{colors.danger}"
    rounded: "{rounded.full}"
    height: 28px
    width: 28px
    borderColor: "rgba(200, 208, 220, 0.92)"
    shadow: "{shadows.floating}"
---

## Overview

This design system is built for a scientific operations dashboard rather than a marketing surface. The interface should feel disciplined, legible, and work-focused. It is meant to support repeated inspection of grayscale mmWave imagery, metric comparison, and ranking decisions without visual noise.

The visual character is "clean lab console": cool gray chrome, white analysis cards, compact controls, and a limited accent palette. Blue drives action and selection. Teal signals positive quality and chart emphasis. Amber and red are reserved for warnings, penalties, and destructive actions. The overall effect should be calm and methodical, with just enough polish to feel modern.

## Implementation Status

This file now describes the implemented baseline on `main`, not just an aspirational concept.

Current implemented decisions:

- The left rail is a unified operator strip for import, streamed progress, and sample browsing.
- Weight controls live in the top-right settings panel rather than in the left rail.
- The sample list is the primary browsing and selection surface. There is no separate ranking gallery or secondary pending list.
- The main viewer is portrait-first, with a vertical feature rail on the right.
- Histograms use a dark, Lightroom-like card treatment.
- Summary information stays compact and does not dominate the viewport.

## Colors

The palette relies on cool neutrals first and semantic accents second.

- **Background neutrals:** The page canvas uses a pale technical gray, while most working surfaces stay pure white. Supporting containers step down through very light blue-gray tones rather than warm grays.
- **Primary blue:** Use the blue range for active controls, selected states, focus affordances, and the main call to action.
- **Success teal:** Use teal and green for good scores, active observation markers, and radar-chart emphasis. This hue should read as analytical confidence, not celebratory branding.
- **Warning and danger:** Amber should appear only on cautionary states. Red is sparse and should be tightly scoped to delete actions, severe flags, and destructive controls.
- **Image framing:** The image stage uses a near-black field so grayscale scans and overlays stay visually isolated from the rest of the dashboard.

Avoid gradients in global page chrome. The only soft tonal transitions should be inside secondary cards such as the feature summary panel.

## Typography

Typography uses a system-first sans stack centered on Inter. The tone is practical and modern, with strong emphasis on dense readability over personality.

- **Headlines:** Section headings are compact and bold. They establish structure but should never dominate the content.
- **Body copy:** Supporting text is small and muted. It is present to clarify context, not to compete with data.
- **Labels and controls:** Labels are bold at small sizes so sliders, chips, tabs, and tables remain scannable.
- **Metrics:** High-priority numeric values use bold, compressed hierarchy. Quality totals and dashboard summary numbers should be the largest values on screen, but still remain modest compared to consumer dashboard styles.

Keep letter spacing neutral. This system does not use editorial tracking or oversized display typography.

## Layout

The desktop layout is a fixed-left-rail dashboard with a fluid analytical workspace to the right.

- **Left rail:** A 380px control column contains import, streamed progress, and sample selection tools. It behaves like a persistent operator console.
- **Main workspace:** The right side splits into a wide image-observation column and a narrower metrics column. On smaller screens, these regions collapse into a single column without changing the visual language.
- **Spacing rhythm:** The interface mostly follows an 8px rhythm with 4px micro-steps. Card interiors use 12px to 20px padding. Larger structural gaps land around 18px to 24px.
- **Density:** This is a dense interface, but not cramped. Each cluster should feel grouped by borders and padding, not by oversized whitespace.

The ranking area is intentionally compact. It should read as a working strip of candidates, not as a gallery. In the current implementation, this strip is the same unified sample list used for selection and batch actions.

## Elevation & Depth

Depth is communicated primarily through borders and tonal separation rather than heavy shadow stacks.

- **Default hierarchy:** Most cards sit flat on the canvas with a 1px cool-gray border.
- **Focus states:** Selection is expressed with a blue border or a light blue focus ring rather than raised elevation.
- **Floating exceptions:** The delete button on ranking tiles is one of the few elements that uses a visible shadow. It should feel like a utility affordance hovering above an image thumbnail.
- **Tooltip depth:** Tooltips are the deepest transient element. They use a dark, opaque background and a stronger drop shadow so they clearly separate from table rows and charts.

If an element can be grouped with color and border alone, do not add more depth.

## Shapes

Shape language is restrained and slightly softened.

- **Standard containers and controls:** Use an 8px radius for most cards, inputs, buttons, tabs, and stage frames.
- **Micro panels:** Small segmented buttons can tighten down to 6px radii where they sit inside a shared control shell.
- **Pills and badges:** Status chips, score pills, and circular action affordances use fully rounded shapes.

There should be no mix of sharp-cornered industrial modules and heavily rounded consumer cards. The system stays consistently in the low-radius range.

## Components

**Buttons** are compact, bordered, and operator-oriented. The primary button is solid blue with white text. Secondary actions stay white with blue text or neutral text depending on importance. Toolbar exports should read as utility controls, not promotional CTAs.

**Segmented controls** sit inside a muted gray tray. The active segment becomes white with blue text and a subtle shadow. Inactive segments stay flat and quiet.

**Import and selection panels** use borders, list dividers, and compact action rows to communicate state. Batch progress appears directly in the import panel as a compact progress card.

**Summary tiles** are simple white rectangles with a muted label and a bold numeric value. They should feel like instrument readouts, but remain compact enough that the sample list keeps priority.

**Image surfaces** consist of a black observation stage with light borders and a separate strip of pill-like overlay toggles. Overlay masks must remain readable against both black background and grayscale scans.

**Ranking tiles** combine an image, small radar overlay, rank badge, score badge, and metadata. The tile should remain legible at a compact size and prioritize scanability over ornament.

**Metric groups** behave like mini tables. Each group has a faint tinted header and thin internal dividers. Tooltip labels should hint interactivity with a dotted underline rather than icon clutter.

**Status chips** are dense, fully rounded labels. They should encode state by background and border color first, with text color reinforcing the meaning.

## Do's and Don'ts

- Do keep the UI neutral and analytical; let the imagery and metrics provide the visual interest.
- Do use blue for control emphasis and teal for quality or success semantics.
- Do frame image content on near-black surfaces so overlays remain readable.
- Do prefer borders and tonal shifts over thick shadows.
- Do keep charts and cards compact enough for side-by-side analysis.
- Don't introduce decorative gradients, glass effects, or marketing-style hero treatments.
- Don't use more than a few accent hues on the same screen.
- Don't inflate spacing or type sizes to make the interface feel "modern"; this product depends on density.
- Don't style whole page sections as floating cards within larger cards.
- Don't use red except for destructive affordances and truly negative states.
