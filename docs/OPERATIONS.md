# Operations

## Daily editorial loop

1. Poll official and first-party sources.
2. Confirm source snapshots landed in the local archive.
3. Pull market reaction context.
4. Cluster and score stories.
5. Review the top slate.
6. Generate draft packages for the best candidates.
7. Confirm the editorial format and style variant fit the story.
8. Verify `claims.json`: factual claims, source URLs, dates, tickers, percentages, and chart framing.
9. Verify `rights_report.json`: official/first-party source posture, provider redistribution review, and missing usage notes.
10. Verify `platform_readiness.json`: original angle, visual transformation, caveat language, and reused-content risk.
11. Verify `approval_checklist.json`: no blockers before approval; warning-level packages need editor notes.
12. Rewrite the hook, chart, or caveat when needed.
13. Record an editor decision: approve, hold, revise, or archive.
14. Export the daily brief for owned-audience distribution.
15. Render the video package only after approval.
16. Publish manually.
17. Archive performance metrics.

## Terminal workflow

Use the CLI when the dashboard is not running:

```powershell
cd C:\Users\Admin\Desktop\market-signal-studio\backend
python -m app.cli catalog
python -m app.cli archive-status
python -m app.cli sec-submissions 0000320193 --limit 5
python -m app.cli fred-observations CPIAUCSL --limit 3
python -m app.cli bls-timeseries CUUR0000SA0 --start-year 2026 --end-year 2026 --limit 3
python -m app.cli gdelt-search "NVDA export controls" --limit 5 --timespan 24h
python -m app.cli slate --limit 5
python -m app.cli export --output-dir ..\exports\latest --limit 3
python -m app.cli newsletter --output-dir ..\exports\daily-brief --limit 3
```

The exported `editor_brief.md` is the human review surface. `preview.html` is the quick visual review surface. `storyboard.json`, `captions.srt`, and `chart_signal.svg` are intended for later Remotion or FFmpeg publishing workers.

The exported `daily_brief.md` is the owned-audience brief for newsletter or email workflows. It should preserve short source citations and avoid republishing article text.

Use `decision_template.json` as the export-side audit stub when a package is reviewed outside the dashboard.

Dashboard decisions are appended to `.runtime/decisions.jsonl` unless `MARKET_SIGNAL_DECISION_LEDGER` points elsewhere. Treat this file as local audit data; do not commit it.

RSS source snapshots are appended to `.runtime/source_archive.jsonl` unless `MARKET_SIGNAL_SOURCE_ARCHIVE` points elsewhere. Treat this file as local audit data; do not commit it.

SEC EDGAR submissions ingestion requires `SEC_USER_AGENT` to be set to a real declared contact string before calling `sec-submissions`.

FRED observations ingestion requires `FRED_API_KEY` before calling `fred-observations`.

BLS time-series ingestion can run without `BLS_API_KEY`, but setting a registered key improves daily and per-request limits.

GDELT discovery ingestion should be treated as recall, not truth. Discovery-only stories should stay held until official or first-party evidence is attached.

## Failure modes

| Failure | Cause | Response |
| --- | --- | --- |
| Wrong ticker | Alias collision or weak entity evidence | Require a second source signal or manual hold |
| Generic script | Template overuse | Switch format variant, rotate hook patterns, and add editor notes |
| Reused-content risk | Too much source recap | Add chart, caveat, and original "why it matters" |
| Platform-readiness warning | Weak transformation or commodity recap language | Rewrite around the data missed, owned visual, and editor caveat |
| Approval rejected | Blocking check or missing notes for warning-level package | Use hold/revise, or add specific approval notes after review |
| Archive count did not change | Feed failed, returned no items, or archive path is misconfigured | Check `archive-status`, feed URL, and provider/user-agent requirements |
| SEC ingestion rejected | Missing declared SEC user agent | Set `SEC_USER_AGENT` to a real app/contact string before retrying |
| FRED ingestion rejected | Missing FRED API key | Set `FRED_API_KEY` before retrying |
| BLS request is throttled | Unregistered public limits or too many series | Set `BLS_API_KEY` and reduce the request window |
| Newsletter brief feels generic | Hooks were not rewritten for owned-audience context | Tighten each signal, caveat, and chart-to-watch line |
| Rights risk | Source license unclear | Hold story until terms are reviewed |
| Market-data risk | Raw quote redistribution | Summarize signal or use licensed provider output |
| Missing primary evidence | Discovery-only story | Archive or hold for editor |
| GDELT-only candidate | Discovery source without official corroboration | Attach SEC, Fed, BLS, FRED, or issuer evidence before approval |

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
- Editorial format fits the story.
- Chart matches the story.
- Platform readiness checked.
- Approval checklist checked.
- Caveat is honest.
- No personalized advice.
- Sponsorship or affiliate disclosures present if relevant.
