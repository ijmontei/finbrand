# Video Production Notes

## Rendered Video Assets

This package includes professional editorial MP4 drafts in `videos/`:

- Ten vertical short-form videos at 1080x1920.
- One horizontal long-form video draft at 1280x720.
- `video_manifest.json` with titles, paths, style labels, and durations.

Each short now follows a stronger consumer-facing financial explainer structure:

- Eye-catching first-screen takeaway.
- Re-created chart from the sourced figures.
- Rights-safe editorial illustration/picture panel.
- Highlight bullets that explain the market implication.
- Bottom-line and watch-next frame.

The videos are suitable for editorial review and brand iteration. They still need a final human playback pass before publishing.

## Renderer

Renderer command:

```powershell
.\scripts\render_professional_videos.ps1 -ShortNumbers 1,2,3,4,5,6,7,8,9,10 -RenderLongform
```

The renderer uses:

- PowerShell and .NET `System.Drawing` for branded editorial frames.
- Re-created bar and line charts using sourced market/economic figures.
- Rights-safe custom illustrations for Fed, consumer, energy, jobs, AI, and market-map visuals.
- Windows `System.Speech` for local narration WAVs.
- `ffmpeg` for zoom/pan motion, fades, MP4 assembly, and audio muxing.

No external video service is required for these drafts.

## Editorial Critique

What is working:

- The videos are no longer static generic cards; each one opens with a large thesis frame.
- The visual system now feels closer to a clean financial explainer format.
- Re-created charts make the evidence more legible for normal consumers.
- The source strip and safety language preserve the rights-aware editorial posture.
- Each short has a distinct market angle and avoids generic headline recap.

What still needs improvement before final publishing:

- Replace local synthetic narration with a recorded voice or higher-quality licensed TTS.
- Add timed captions or per-beat kinetic text for mobile retention.
- Add source lower-thirds or QR/source cards for platform trust.
- Add licensed or owned photographic/video footage if the final channel wants real-world B-roll.
- Run a final human playback pass for pacing, pronunciation, and factual emphasis.

## Best First Video To Polish

Start with either:

- `03-core-cpi-looked-better-energy-did-not.mp4`
- `05-ai-demand-is-real-the-multiple-is-the-question.mp4`

These have the strongest brand fit because they turn a messy finance topic into a simple visual contrast:

- Core versus energy.
- Demand versus valuation.
- Data point versus market implication.
