---
name: PredictKit
description: A precise, inspectable workspace for turning a prediction question into a working application.
colors:
  canvas: '#080D16'
  surface: '#111B29'
  surface-raised: '#192638'
  text: '#F3F7FC'
  muted: '#AAB9CD'
  border: '#384B64'
  control-border: '#748BA8'
  accent: '#62E8CE'
  accent-ink: '#06221C'
  secondary: '#AB91F2'
  success: '#77E4B5'
  warning: '#F3CE7E'
  danger: '#FFACB7'
  focus: '#62E8CE'
  chart-yes: '#62E8CE'
  trust-canvas: '#F5F7FB'
  trust-surface: '#FFFFFF'
  trust-surface-raised: '#EAF0F8'
  trust-text: '#152033'
  trust-muted: '#536179'
  trust-border: '#CAD5E5'
  trust-control-border: '#697B94'
  trust-accent: '#2455D6'
  trust-accent-ink: '#FFFFFF'
  trust-secondary: '#7553BA'
  trust-success: '#126443'
  trust-warning: '#805700'
  trust-danger: '#AF2742'
  trust-focus: '#2455D6'
  trust-chart-yes: '#11765F'
  classic-canvas: '#F4F4ED'
  classic-surface: '#FFFEF9'
  classic-surface-raised: '#EEF1E7'
  classic-text: '#192D2B'
  classic-muted: '#52635B'
  classic-border: '#C8D2C1'
  classic-control-border: '#73806B'
  classic-accent: '#DCE9A7'
  classic-accent-ink: '#192D2B'
  classic-secondary: '#7D5C94'
  classic-success: '#365A38'
  classic-warning: '#815535'
  classic-danger: '#9B3A30'
  classic-focus: '#4E7047'
  classic-chart-yes: '#2E6B55'
  signal: '#62E8CE'
  trust-signal: '#2455D6'
  classic-signal: '#4E7047'
typography:
  display:
    fontFamily: '"Space Grotesk", Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: clamp(52px, 5.9vw, 84px)
    fontWeight: 600
    lineHeight: 0.99
    letterSpacing: -.04em
  headline:
    fontFamily: '"Space Grotesk", Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: 44px
    fontWeight: 600
    lineHeight: 1.11
    letterSpacing: -.035em
  catalog-headline:
    fontFamily: '"Space Grotesk", Inter, sans-serif'
    fontSize: clamp(32px, 3.3vw, 48px)
    fontWeight: 600
    lineHeight: 1.13
    letterSpacing: -.035em
  title:
    fontFamily: '"Space Grotesk", Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: 20px
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: -.45px
  body:
    fontFamily: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif
    fontSize: 14px
    lineHeight: 1.5
  body-landing:
    fontFamily: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif
    fontSize: 16px
    lineHeight: 1.5
  label:
    fontFamily: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif
    fontSize: 12px
    fontWeight: 600
    lineHeight: 1.5
  action-landing:
    fontFamily: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif
    fontSize: 14px
    fontWeight: 600
    lineHeight: 1.4
  input:
    fontFamily: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif
    fontSize: 13px
    lineHeight: 1.5
  forecast-data:
    fontFamily: '"JetBrains Mono", "SFMono-Regular", Consolas, monospace'
    fontSize: 28px
    fontWeight: 500
    lineHeight: 1
    letterSpacing: -1px
  source:
    fontFamily: ui-monospace, SFMono-Regular, Menlo, monospace
    fontSize: 12px
    lineHeight: 1.75
rounded:
  panel: 16px
  control: 9px
  tag: 5px
  role-choice: 8px
  notice: 12px
  dialog: 18px
spacing:
  space-1: 4px
  space-2: 8px
  space-3: 12px
  space-4: 16px
  space-6: 24px
  space-8: 32px
  space-12: 48px
  space-16: 64px
components:
  button-primary:
    backgroundColor: '{colors.accent}'
    textColor: '{colors.accent-ink}'
    typography: '{typography.label}'
    rounded: '{rounded.control}'
    padding: 11px 16px
  button-quiet:
    backgroundColor: '{colors.surface}'
    textColor: '{colors.text}'
    typography: '{typography.label}'
    rounded: '{rounded.control}'
    padding: 11px 16px
  button-landing:
    backgroundColor: '{colors.accent}'
    textColor: '{colors.accent-ink}'
    typography: '{typography.action-landing}'
    rounded: '{rounded.control}'
    padding: 13px 22px
  input:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.text}'
    typography: '{typography.input}'
    rounded: '{rounded.control}'
    padding: 11px 12px
  tag:
    backgroundColor: '{colors.surface-raised}'
    textColor: '{colors.muted}'
    rounded: '{rounded.tag}'
    padding: 5px 8px
  panel:
    backgroundColor: '{colors.surface}'
    textColor: '{colors.text}'
    rounded: '{rounded.panel}'
  role-choice:
    backgroundColor: '{colors.surface}'
    textColor: '{colors.text}'
    rounded: '{rounded.role-choice}'
    padding: 11px 12px
---

# Design System: PredictKit

## Overview

**Creative North Star: "The inspectable prediction workspace"**

PredictKit keeps its supplied checkpoint mark and three-theme identity. The visual character is precise, readable and technical: clear decisions, compact working surfaces, visible source and forecast data, with mint and purple accents that connect the interface to its intended Solana foundation.

The system serves builders first. Space Grotesk headings give the product a distinct voice; Inter carries the interface; monospaced traces distinguish numerical and source material. The appearance can feel like a trading workspace while its labels continue to say what is illustrative, rehearsed, off-chain or not connected.

**Key Characteristics:**

- One checkpoint identity across Solana Signal, Trust Layer and Studio Classic.
- Dense work surfaces paired with a more spacious explanatory landing page.
- Forecast data and source inspection provide the technical character.
- Visible state, keyboard focus and reduced-motion behavior remain part of the interface.

This is a scan of the implemented system, not a new visual concept. Sources: [Studio styles](web/studio.css), [landing styles](web/landing.css), [role-catalog styles](web/skills.css), [local font faces](web/fonts.css) and their HTML counterparts. [PRODUCT.md](PRODUCT.md) supplies the durable identity and evidence boundaries. Token values come from these stylesheets; responsive overrides remain surface-specific.

## Colors

Solana Signal is a cool dark workspace with mint action color and purple counterpoint. Trust Layer uses pale blue-white surfaces with blue actions. Studio Classic keeps the cream, ink and lime identity with forest and plum data accents.

The frontmatter uses the unprefixed source roles for **Solana Signal**, `trust-` for **Trust Layer**, and `classic-` for **Studio Classic**. The prefix is a documentation namespace; the application selects `data-theme` and overrides the same CSS properties.

### Primary

- **Accent / accent ink:** the filled primary action and its contrasting text in each theme.
- **Signal:** readable foreground accents, checkpoint strokes and catalog role markers, plus the landing's headline accent and chart. It follows the action accent in Solana Signal and Trust Layer, and uses a stronger forest tone in Studio Classic.
- **Chart YES:** the Studio's affirmative forecast and first Solana stripe. It is mint in the dark theme and forest in the light themes.

### Secondary

- **Secondary:** the purple or plum counterpoint, the Studio NO series and the final Solana stripe. The middle stripe mixes the YES and secondary roles.

### Tertiary

- **Success, warning, danger:** status and intervention colors. Keep their descriptive labels; color alone is not a complete state.
- **Focus:** the keyboard outline color. Studio Classic uses a darker forest focus color instead of its pale action fill.

### Neutral

- **Canvas → surface → surface raised:** page, primary working container and nested or selected regions.
- **Text / muted:** primary content and secondary explanations.
- **Border / control border:** structural divisions and the stronger perimeter of editable or actionable controls.

**The Three-theme continuity Rule.** Preserve the same semantic roles across all three appearances. A theme changes the palette, not the meaning of an approval, warning or forecast.

**The Readable Classic accents Rule.** Studio Classic uses lime for filled primary actions; its informational accents use ink, forest or plum. Do not turn the pale action fill into a general text color.

The sidecar's tonal strips are synthesized preview metadata, not additional shipped CSS colors. Do not substitute them for the frontmatter primitives.

## Typography

**Display Font:** local Space Grotesk, with Inter and system sans fallbacks.

**Body Font:** local Inter, followed by the platform sans stack.

**Data / Source Fonts:** the Studio and landing declare JetBrains Mono with SFMono-Regular/Consolas/monospace fallbacks; the source catalog uses ui-monospace/SFMono-Regular/Menlo. JetBrains Mono is not bundled by `fonts.css`; do not claim a third local font asset.

The pairing combines compact geometric headings with readable interface text. Local font files use `font-display: swap`; Space Grotesk provides variable weights 300–700 and Inter 100–900.

### Hierarchy

- **Display:** the landing's fluid hero, with surface-specific responsive clamps.
- **Headline:** the Studio's main heading; the catalog has its own fluid headline role.
- **Title:** the Studio section heading, with smaller panel-heading and larger landing-section variants.
- **Body:** the compact Studio base; the landing has a roomier base. Explanatory paragraphs commonly use line heights from 1.65 to 1.8.
- **Label / action:** compact controls and status text. Functional type is at least 12px in the current stylesheets.
- **Forecast data:** monospaced probability figures with tabular numeric treatment; source viewers use a separate line-height suited to reading files.

Studio inputs increase to 16px on small screens. The recorded scale is role-based, not a single fixed mathematical ratio. Do not normalize all surfaces to one heading size or body density.

**The Display and data separation Rule.** Use Space Grotesk for headings, Inter for interface prose and controls, and the recorded monospace stacks for probabilities, source, identifiers and logs.

## Layout

The Studio is a working application: a sticky 224px navigation rail and a flexible main area capped at 1660px. Its content pairs a flexible main panel with a 300px inspector, becoming 340px on wide screens and 265px in the intermediate layout. The two-column brief form uses a 22px by 18px gap. Panels use 24px body padding at the standard desktop size.

At 1240px the Studio rail and horizontal padding tighten. At 1040px the inspector moves below the primary panel. At 780px the rail becomes a top region with horizontally scrollable navigation. At 560px the fields and inspector stack; content gutters reduce to 18px and inputs grow to the mobile text size. The forecast specimen stays beneath the working context rather than forcing the desktop arrangement onto a narrow screen.

The landing uses a centered 1280px maximum content width and 48px desktop side margins. The hero has two equal flexible columns with a 72px gap. Explanatory sections use broad vertical separation and ruled divisions rather than a wall of cards. Breakpoints at 1200px and 900px tighten the layout; at 640px the hero and explanatory split sections stack with 20px side margins. At 360px the page uses 16px side margins.

The role catalog has a 1312px main maximum and a 232px sticky directory beside the role detail. At 1050px the directory reduces to 200px; at 760px it becomes a two-column choice list above the detail. Source content wraps long paths and hashes. On mobile the runtime comparison stacks each row, with its column labels repeated beside the content.

The shared spacing vocabulary uses the frontmatter's small 4px steps and larger 24/32/48/64px intervals. Real layouts also contain content-driven gaps and paddings; the scale is not permission to rewrite those established relationships.

## Elevation & Depth

Routine panels are separated by borders and tonal surfaces. The landing forecast demonstration and the Studio dialog use diffuse elevation. The light landing shadows are less opaque than their Studio counterparts; this is an existing surface difference, not a new global token.

### Shadow Vocabulary

- **Studio elevated layer:** `0 12px 32px #0005` in Solana Signal, `0 12px 32px #15203322` in Trust Layer and `0 12px 32px #192D2B22` in Studio Classic.
- **Landing forecast:** the same dark shadow; the light-theme variants use the existing `15` alpha suffix.
- **Landing primary hover:** `0 6px 22px #0002`, paired with a small upward shift on precise pointing devices.
- **Studio primary hover:** a 3px accent-mix ring; this is state feedback, not a card shadow.
- **Modal backdrop:** translucent near-black with 5px blur, distinct from the dialog's own border and shadow.

**The Surface before shadow Rule.** Borders and the canvas/surface/raised-surface sequence organize routine work. Reserve diffuse elevation for the forecast demonstration and modal layers.

## Shapes

Rounded rectangles are the dominant form. Working panels and role cards use the panel radius; controls use the smaller control radius. Tags, compact role choices and notices have their own recorded corners. A desktop dialog uses the dialog radius, reducing to 13px on small screens. Most structure uses a 1px stroke.

The checkpoint is the recurring brand shape: an open diamond and check drawn as an SVG stroke. Preserve its geometry and stroke character. Small circles mark state or series identity; the Solana foundation uses three SVG stripes with the observed mint-to-purple relationship. These marks do not establish network connectivity or affiliation.

## Components

### Buttons

Compact and explicit. Studio actions use a 44px minimum height; the landing's main actions use a 52px minimum, with a compact 44px header variant. Primary buttons use accent fill and accent ink. Secondary controls use the surface or a transparent landing background with a control border. Studio Classic gives primary actions a stronger control border.

Studio primary hover adds a slight brightness change and a subtle accent ring; quiet controls change their surface. On fine pointers, Studio press feedback scales to .98. Landing primary hover moves upward by 2px and adds its recorded shadow. All keyboard actions retain the visible focus treatment. Disabled actions use reduced opacity and a blocked cursor.

### Chips

Tags are compact, bordered metadata on a raised surface. Status chips combine a dot with words; warnings also change the border. Do not rely on a dot or hue without the text state. Tags describe evidence, modes or outputs; they are not generic decorative labels.

### Cards / Containers

Studio panels contain a ruled heading, body and optional footer. Use the shared surface and border, with the frontmatter panel radius. The role card follows the same form but allocates more space to its title, contract, assigned skills and source disclosures. Ordinary cards do not need a shadow.

### Inputs / Fields

Editable fields sit on the canvas tone inside a surface panel, with a stronger control border, the control radius and a minimum 44px height. Labels sit above the field. Hover raises border contrast; keyboard focus uses the theme focus color. Long brief answers belong in auto-sizing textareas; the project name retains a single-line field. The two-column form stacks on small screens.

### Navigation

Studio navigation uses numbered stages with a 46px desktop minimum height. Hover introduces the raised surface; the active item uses a tinted accent treatment. Studio Classic uses its filled accent with ink text. The landing navigation is lighter, using muted text that becomes the signal color on hover. The catalog exposes its active destination and role choice with semantic selection attributes and visible contrast.

### Forecast specimen

A labeled, inspectable illustration anchors the prediction identity. The Studio pairs YES and NO numbers with solid and dashed SVG paths and an explicit example caption. The landing demonstration adds scenario choices, a probability range and outcome controls. Use native inputs, visible output values and an accessible chart description. A probability is not an exchange price; a sample path is not a live feed.

### Role and source inspection

The catalog exposes role contracts, assigned skills, file paths and hashes. Its source blocks use a canvas inset, strong border, wrapped monospace text and a bounded scroll area. Disclosure and copy controls remain real controls. Source visibility explains the mechanism; it must not imply that a file was executed merely because it is displayed.

### Motion and focus

State transitions use the existing 160ms duration. The Studio and landing currently use different easing curves, recorded separately in the sidecar. The landing chart entrance is 700ms and only runs when reduced motion is not requested. Studio and catalog suppress transitions for reduced-motion users. Focus is visibly outlined: Studio uses 3px with a 4px offset, landing 3px with a 5px offset, and the catalog 2px with a 4px offset.

## Do's and Don'ts

### Do:

- **Do** preserve the checkpoint mark, the three existing themes and their semantic color assignments.
- **Do** keep runtime and network state visible beside the controls or data it qualifies.
- **Do** label illustrative forecasts and preserve YES/NO labels and the dashed NO line in the Studio specimen.
- **Do** retain readable functional text, visible keyboard focus and reduced-motion behavior.
- **Do** use the existing bordered panel, source viewer and native control patterns when extending the interface.

### Don't:

- **Don't** imply a connected wallet, market feed, live trade or deployed registry through decorative trading cues.
- **Don't** use Studio Classic's pale lime fill as body or informational text.
- **Don't** replace the local Space Grotesk and Inter pairing with a system display face.
- **Don't** promote leftover decorative kickers or text-glyph icons into reusable design rules.


## Capability increment — 28 September 2026

The role catalog now groups practical actions and an example before exact files, static checks and human review questions. Boundaries and source text use native disclosures. The Studio role dialog distinguishes prepared inputs, observed check results and assembled-request evidence; absent/legacy records remain explicit. The existing three palettes, typography and focus tokens are unchanged. Twelve desktop/mobile captures and independent visual/contrast evidence are recorded in `evidence/capabilities-2026-09-28/`.
