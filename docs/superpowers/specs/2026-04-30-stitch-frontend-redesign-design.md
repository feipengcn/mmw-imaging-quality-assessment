# mmWave Frontend Stitch Redesign

Date: 2026-04-30
Status: Approved for implementation planning

## Goal

Redesign the frontend of the mmWave image quality assessment application to follow the approved Stitch workbench structure while preserving the current backend APIs, core data model, and analysis workflow.

The redesign is not a visual reskin only. It restructures the page into a denser operator-facing workbench that is better aligned with the actual usage pattern:

- import samples
- sort and inspect the sample list
- batch-select and calculate
- switch the current sample
- inspect overlays and metrics
- manage low-frequency settings separately from high-frequency sample operations

## Design Summary

The approved layout is a three-zone analysis workbench:

1. Left rail: compact import controls and the primary sample operations list
2. Center stage: vertical image viewer with overlay switching and a narrow histogram rail
3. Right rail: explanatory metrics for the current sample

Global summary values remain visible but are reduced to compact badges in the upper corner of the center area. Low-frequency settings move into the existing top-right settings entry instead of occupying persistent left-rail space.

## Layout

### Top Bar

The top bar remains fixed and lightweight.

It contains:

- product title / workbench identity
- primary section navigation
- status and notification affordances
- a settings entry in the top-right corner

The settings entry becomes the home for configuration that does not need to remain permanently visible during sample review.

### Left Rail

The left rail is the only high-frequency operations surface.

It contains:

- import mode toggle: file import / folder import
- compact import drop/select strip
- sortable sample list
- list-level actions

It does not contain:

- descriptive onboarding text
- redundant status cards
- a standalone "start analysis" button
- persistent weight controls
- a separate ranked gallery

This rail should maximize vertical space for visible sample rows.

### Center Stage

The center stage is for image observation only.

It contains:

- compact global summary badges in a corner
- a vertically-oriented primary viewer for the current sample
- overlay mode switching: original / AOI / leakage / stripe
- a narrow vertical histogram rail adjacent to the main viewer

The main viewer must favor portrait presentation because the common image orientation is portrait and the previous horizontal layout wasted screen area.

### Right Rail

The right rail is an explanatory panel for the current sample.

It contains:

- quality radar
- status chips
- physical metrics detail list

It does not own navigation or batch operations.

## Component Mapping

### Import

Existing import functionality remains, but is compressed into the top of the left rail.

Current behavior to preserve:

- file import
- folder import
- drag/drop or click-to-select
- import preview behavior where applicable

The redesign changes presentation, not capability.

### Sample List

The existing pending/import list and the separate ranked sample area are merged into one main sample list.

Each row in the list is responsible for:

- showing the sample identity
- showing the current score when available
- reflecting selected-for-batch state
- reflecting current-focused sample state
- switching the current sample on row click

The list becomes both the browsing surface and the ranked surface.

### Sorting

The sample list supports at least two sort modes:

- by score
- by filename

Default behavior:

- by score when scored samples are present
- descending score order

Filename sorting uses the display filename/path the user already sees.

Sorting is a frontend-derived view and must not require backend changes.

### Batch Actions

Batch and row-level actions remain attached to the left rail.

Required actions:

- calculate selected
- select all / clear
- focus current only
- delete current
- delete selected

"Focus current only" is a view filter only. It must not mutate the data source.

If the current sample is deleted, the app should automatically move focus to the next available row, falling back to the first available row, then null if empty.

### Main Viewer

The current selected sample drives the center viewer.

The center viewer supports:

- original image
- AOI overlay
- leakage overlay
- stripe overlay

The current overlay mode remains local UI state and should not alter scoring data.

### Histograms and Image Features

The approved interpretation of "image features" is:

- resolution
- color mode
- grayscale histogram
- RGB histograms

The redesign places the histograms in a narrow vertical rail beside the main viewer. Resolution and mode become compact textual metadata rather than full-width cards.

### Right-Rail Metrics

The current selected sample also drives:

- radar chart
- status chips
- physical metric groups

These panels update immediately when the current sample changes.

## Settings Model

Persistent left-rail weight controls are removed from the main page.

The top-right settings entry becomes the future home for:

- weight control
- theme selection: light / dark
- language selection
- future low-frequency display or behavior settings

For implementation, the first required migration is weight control.

The settings entry can first ship as:

- a popover
- a drawer
- a modal

Recommendation: use a popover or side panel first, because the settings are operational but not full-screen tasks.

## State and Data Flow

The redesign should preserve the existing backend contract and most current frontend state.

Current state expected to remain useful:

- `images`
- `selectedId`
- `weights`
- `importMode`
- `importEntries`
- `selectedImportIds`
- `selectedImportIndex`
- `overlayMode`
- `busy`
- `message`

Required behavioral clarification:

- `selectedImportIds` is for batch calculation selection
- `selectedId` is for the currently focused sample in the viewer and right rail
- sort mode is a derived UI state
- "focus current only" is a derived UI filter state

The redesign should avoid introducing backend-dependent layout behavior.

## Error Handling

The current error model should stay intact and remain visible in the redesigned layout.

Required expectations:

- import failure still surfaces a visible message
- calculate failure still surfaces a visible message
- delete failure still surfaces a visible message
- empty-state handling remains clear when there are no samples
- empty current-selection behavior remains stable after deletion or reset

The redesign should not hide operational feedback inside settings or non-obvious surfaces.

## Responsiveness

Desktop is the primary target.

Expected responsive behavior:

- desktop: full three-zone workbench
- medium screens: left rail plus center, right rail may wrap below
- small screens: stacked layout, but sample list still appears before metrics

The portrait-oriented main viewer and the left-rail list must remain readable at reduced widths.

## Out of Scope

This design does not require:

- backend API changes
- new scoring logic
- new export formats
- new image-processing algorithms
- finalized dark-mode implementation details beyond the settings placeholder
- finalized localization framework beyond a language setting destination

## Implementation Constraints

- preserve current backend endpoints and response shapes
- preserve current testable workflows for import, calculate, rescore, reset, and delete
- avoid introducing a second ranked surface
- avoid duplicating controls between left rail and top bar settings
- keep the main workbench optimized for repeated analyst use rather than presentation

## Testing Expectations

Implementation should verify:

- import controls still work for files and folders
- sorting by score and name works predictably
- current sample selection drives center and right rails correctly
- calculate selected uses checkbox selection, not current focus alone
- delete current and delete selected behave correctly
- focus transitions are stable after deletion
- overlay switching still works
- radar and metric panels still update with the current sample
- weight controls still function after moving into settings
- mobile and medium layouts do not collapse into overlapping content

## Recommended Implementation Order

1. Restructure layout shells and move ranked area into the left list
2. Add sort mode and unify list responsibilities
3. Convert center viewer to portrait-first composition with histogram rail
4. Move weight controls into the settings entry
5. Reflow summary badges and right-rail metric sections
6. Update and extend frontend tests for the new interaction model
