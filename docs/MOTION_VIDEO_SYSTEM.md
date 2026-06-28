# Motion-First Video System

This repo now includes a motion-first flagship template for source-backed market explainers.

## Current Flagship Template

Template: Fed / policy reaction  
Story: `2026-06-28-fed-pause-not-pivot-v03`  
Visual intent: `target_gap`  
Theme: `dark_market`

The template is generated from:

- `content/2026-06-28-market-signal/stories/fed-pause-not-pivot.json`
- `scripts/render_motion_first_fed_video.ps1`

## Render Command

```powershell
.\scripts\render_motion_first_fed_video.ps1
```

The command exports:

- MP4 master.
- Thumbnail.
- Captions SRT.
- Source manifest JSON.
- Render manifest JSON.
- QA JSON.
- Safe-zone contact sheet.
- Platform caption draft.
- Local review page.

It also replaces `videos/01-the-fed-did-not-blink.mp4` with the flagship render and updates the package `video_manifest.json`.

## Component Model

Implemented components:

- `BrandHeader`
- `TopicPill`
- `HookHeadline`
- `BigNumber` / metric chips
- `RatePath`
- `TargetGap`
- `ImpactTiles`
- `WatchNext`
- `SourceCapsule`
- `SafeZoneOverlay`
- `MarketTicker`

The current renderer draws frames directly with .NET `System.Drawing`, then encodes with FFmpeg. The structure is intentionally compatible with a future Remotion/React migration: story data, scenes, metrics, source metadata, timing, and QA artifacts are already separated from the renderer.

## QA Gates

Current automated QA writes:

- Safe-zone status.
- Contrast ratios.
- Text overflow status.
- Chart-label status.
- Source metadata status.
- Data-integrity status.
- Blank-frame status.
- Motion-cadence status.
- Audio encoding status.

Current export target:

- 1080x1920.
- 30 fps.
- H.264.
- AAC, 48 kHz, stereo.
- Loudness-normalized audio filter.

## Review Page

Open:

```text
content/2026-06-28-market-signal/videos/flagship/review.html
```

The page gives a non-programmer review surface for the MP4, thumbnail/poster frame, QA contact sheet, captions, source manifest, render manifest, QA JSON, and platform caption draft.

## Next Template Targets

The Fed template should be used as the pattern for:

- Inflation / target gap.
- Earnings / actual versus expected.
- AI capex / demand versus valuation.
- Jobs / labor stability.
- Energy / headline pressure.

Each new template should start with a structured JSON story object and fail review if any metric lacks unit, source, period, and as-of date.
