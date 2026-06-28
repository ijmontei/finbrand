# Video Production Notes

## Rendered Video Assets

This package includes actual MP4 drafts in `videos/`:

- Ten vertical short-form videos at 1080x1920.
- One horizontal long-form video draft at 1280x720.
- `video_manifest.json` with titles, paths, and durations.

The videos are intentionally draft-grade: branded visuals, local voiceover, source-aware captions, and finance-safety language are present. They are suitable for editorial review, not final upload without a human playback pass.

## Renderer

Renderer command:

```powershell
.\scripts\render_content_videos.ps1 -ShortNumbers 1,2,3,4,5,6,7,8,9,10 -RenderLongform
```

The renderer uses:

- PowerShell and .NET `System.Drawing` for branded slide frames.
- Windows `System.Speech` for local narration WAVs.
- `ffmpeg` for MP4 assembly.

No external video service is required for these drafts.

## Editorial Critique

What is working:

- The videos now exist as actual publish-review artifacts, not just scripts.
- The visual system matches the finance brand palette.
- Each short has a distinct market angle and avoids generic headline recap.
- The voiceover preserves the "explain the signal" tone.

What still needs improvement before final publishing:

- Replace local synthetic narration with a recorded voice or higher-quality licensed TTS.
- Add subtle motion between cards, not only static slide cuts.
- Add source lower-thirds or QR/source cards for platform trust.
- Add waveform/caption timing if the final format uses burned-in subtitles.
- Run a final human playback pass for pacing, pronunciation, and factual emphasis.

## Best First Video To Polish

Start with `05-ai-demand-is-real-the-multiple-is-the-question.mp4`.

It has the strongest brand fit because it separates the business story from the stock-valuation story:

- AI demand is real.
- Valuation is still rate-sensitive.
- A great company can still face multiple compression.

