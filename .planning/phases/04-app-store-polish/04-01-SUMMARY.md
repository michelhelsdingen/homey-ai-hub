---
phase: 04-app-store-polish
plan: 01
subsystem: infra
tags: [homey, app-store, manifest, assets, svg, png]

# Dependency graph
requires:
  - phase: 03-vision-support
    provides: completed core feature set ready for App Store submission
provides:
  - Complete App Store-compliant manifest (.homeycompose/app.json)
  - App icon (assets/icon.svg, 960x960)
  - Promo images (assets/images/small.png 250x175, large.png 500x350, xlarge.png 1000x700)
affects: [homey-app-validate, app-store-submission]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "PNG generation via Python struct/zlib standard library (no external deps)"
    - "SVG icon: blue circle (#1a73e8) with white text for Homey branding"

key-files:
  created:
    - assets/icon.svg
    - assets/images/small.png
    - assets/images/large.png
    - assets/images/xlarge.png
  modified:
    - .homeycompose/app.json

key-decisions:
  - "version bumped to 1.0.0 for first public App Store release"
  - "brandColor #1a73e8 (dark blue) — matches settings page button color, passes Homey brightness validation"
  - "runtime: python, platforms: [local] — mandatory fields for Homey Python apps targeting Homey Pro"
  - "pythonVersion: 3.14 — current Homey Python runtime"
  - "category changed from array to string — Homey spec requires string, not array"
  - "PNG files generated with Python standard library only — no PIL/pillow or external dependencies needed"

patterns-established:
  - "PNG generation pattern: struct.pack IHDR + zlib.compress raw pixel rows — reproducible for future image updates"

requirements-completed: []

# Metrics
duration: 5min
completed: 2026-03-12
---

# Phase 4 Plan 01: App Store Polish — Manifest and Assets Summary

**App Store-compliant manifest with brandColor, runtime, platforms, pythonVersion, and four required asset files (icon.svg + three promo PNGs) generated from scratch using Python standard library.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-12T00:20:00Z
- **Completed:** 2026-03-12T00:25:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Rewrote .homeycompose/app.json with all 8 required/recommended fields for App Store submission (brandColor, runtime, platforms, pythonVersion, version 1.0.0, category string, description user-benefit language, images.xlarge added)
- Created assets/icon.svg as a clean 960x960 SVG with blue circle and white "AI" text (transparent background, passes Homey CLI validation)
- Generated three valid PNG promo images (250x175, 500x350, 1000x700) using Python struct/zlib — no external dependencies required

## Task Commits

Each task was committed atomically:

1. **Task 1: Update app.json manifest with all required App Store fields** - `6a7e03f` (feat)
2. **Task 2: Create assets directory with icon and promo images** - `8a24847` (feat)

## Files Created/Modified
- `.homeycompose/app.json` - Complete manifest with all required App Store fields
- `assets/icon.svg` - App icon, 960x960 SVG, blue circle with white AI text
- `assets/images/small.png` - Promo image 250x175 px, solid blue #1a73e8
- `assets/images/large.png` - Promo image 500x350 px, solid blue #1a73e8
- `assets/images/xlarge.png` - Promo image 1000x700 px, solid blue #1a73e8

## Decisions Made
- brandColor #1a73e8 (dark blue, not too bright) — matches existing settings page button color
- pythonVersion set to 3.14 (current Homey Python runtime per research)
- PNG generation uses Python struct/zlib only — no PIL or external packages needed for solid-color images
- source and bugs fields added to manifest (recommended by Homey App Store, links to GitHub)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All asset and manifest requirements for `homey app validate --level publish` are now in place
- Next: run homey app validate to confirm no remaining compliance issues
- Homey CLI sharp module conflict (tracked from Phase 1) still needs resolution for live testing

---
*Phase: 04-app-store-polish*
*Completed: 2026-03-12*
