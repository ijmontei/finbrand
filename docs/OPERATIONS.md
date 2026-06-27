# Operations

## Daily editorial loop

1. Poll official and first-party sources.
2. Pull market reaction context.
3. Cluster and score stories.
4. Review the top slate.
5. Generate draft packages for the best candidates.
6. Verify factual claims, source URLs, dates, tickers, and percentages.
7. Rewrite the hook or caveat when needed.
8. Render the video package.
9. Publish manually.
10. Archive performance metrics.

## Terminal workflow

Use the CLI when the dashboard is not running:

```powershell
cd C:\Users\Admin\Desktop\market-signal-studio\backend
python -m app.cli catalog
python -m app.cli slate --limit 5
python -m app.cli export --output-dir ..\exports\latest --limit 3
```

The exported `editor_brief.md` is the human review surface. `preview.html` is the quick visual review surface. `storyboard.json`, `captions.srt`, and `chart_signal.svg` are intended for later Remotion or FFmpeg publishing workers.

## Failure modes

| Failure | Cause | Response |
| --- | --- | --- |
| Wrong ticker | Alias collision or weak entity evidence | Require a second source signal or manual hold |
| Generic script | Template overuse | Rotate hook patterns and add editor notes |
| Reused-content risk | Too much source recap | Add chart, caveat, and original "why it matters" |
| Rights risk | Source license unclear | Hold story until terms are reviewed |
| Market-data risk | Raw quote redistribution | Summarize signal or use licensed provider output |
| Missing primary evidence | Discovery-only story | Archive or hold for editor |

## Language guardrails

Prefer:

- "The market is reacting to..."
- "The data investors are watching is..."
- "This does not prove the trend yet..."
- "The caveat is..."

Avoid:

- "You should buy..."
- "You should sell..."
- "Guaranteed..."
- "Can't miss..."
- "Price target..."
- "This will 10x..."

## Editor checklist

- Tickers verified.
- Dates verified.
- Price and volume numbers verified.
- Source trail attached.
- Chart matches the story.
- Caveat is honest.
- No personalized advice.
- Sponsorship or affiliate disclosures present if relevant.
