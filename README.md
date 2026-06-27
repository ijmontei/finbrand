# Market Signal Studio

Market Signal Studio is a rights-aware editorial engine for short-form finance content. It is built around the stronger version of the idea: automated signal detection, source-grounded research packets, original commentary, visual explanation, and human approval before anything gets published.

The first product lane is:

> Why stocks moved today, explained with data instead of vibes.

## What is included

- Python editorial engine for source normalization, entity mapping, story clustering, ranking, script drafting, chart ideas, and compliance QA.
- FastAPI backend exposing story, package, RSS ingest, and QA endpoints.
- React dashboard for reviewing the story slate, source trail, scoring rationale, generated script, and publishing gates.
- Daily brief export for newsletter or owned-audience distribution.
- Audited editor overrides for rare primary-source exceptions.
- Structured source-terms reviews for provider licensing and restrictions.
- Sample primary-source-style records so the app runs before paid APIs or data licenses are added.
- Documentation for source policy, roadmap, and operating model.

## Why this shape

The project intentionally avoids the fragile version of "AI reads financial headlines." Discovery APIs can help find candidates, but the durable product is a source-verifiable editorial workflow. The system should be able to answer:

- What happened?
- Who or what did it affect?
- What market signal says it mattered?
- What primary or first-party source backs the claim?
- What chart would make the explanation clearer?
- What is still uncertain?

## Local setup

### Backend

```powershell
cd C:\Users\Admin\Desktop\market-signal-studio\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

### Frontend

```powershell
cd C:\Users\Admin\Desktop\market-signal-studio\frontend
npm install
npm run dev
```

The dashboard will be available at the Vite URL printed in the terminal, usually `http://127.0.0.1:5173`.

### Core tests

```powershell
cd C:\Users\Admin\Desktop\market-signal-studio\backend
python -m unittest discover -s tests
```

### Headless editorial workflow

The backend also includes a CLI for producing editor-ready files without opening the dashboard:

```powershell
cd C:\Users\Admin\Desktop\market-signal-studio\backend
python -m app.cli catalog
python -m app.cli archive-status
python -m app.cli sec-submissions 0000320193 --limit 5
python -m app.cli fred-observations CPIAUCSL --limit 3
python -m app.cli bls-timeseries CUUR0000SA0 --start-year 2026 --end-year 2026 --limit 3
python -m app.cli gdelt-search "NVDA export controls" --limit 5 --timespan 24h
python -m app.cli market-csv ..\data\market-reactions.csv --source-name "Licensed desk export"
python -m app.cli review-source-terms "Licensed desk export" --source-type market_data --review-status approved_publish --terms-url "internal://terms/market-data" --allowed-use "May publish derived market reaction values with attribution." --restrictions "No raw quote feed redistribution."
python -m app.cli source-terms
python -m app.cli slate --limit 3
python -m app.cli override-primary-source STORY_ID --reason "Editor reviewed alternate evidence..." --evidence-url "internal://editorial/source-review/123"
python -m app.cli export --output-dir ..\exports\latest --limit 3
python -m app.cli newsletter --output-dir ..\exports\daily-brief --limit 3
```

Each exported story folder contains:

- `story.json`
- `package.json`
- `qa.json`
- `claims.json`
- `rights_report.json`
- `platform_readiness.json`
- `approval_checklist.json`
- `asset_manifest.json`
- `chart_signal.svg`
- `storyboard.json`
- `captions.srt`
- `preview.html`
- `decision_template.json`
- `editor_brief.md`

Slate exports also include `daily_brief.md` and `daily_brief.json` for a newsletter or owned-audience daily brief. These reuse the same source trail, approval status, rights status, caveat, and chart idea as the video workflow.

Configured official feeds can be inspected with `python -m app.cli catalog`. A single configured feed can be pulled with `python -m app.cli ingest-feed fed_monetary_policy`. Recent SEC submissions can be pulled by CIK with `python -m app.cli sec-submissions 0000320193 --limit 5`. FRED macro observations can be pulled with `python -m app.cli fred-observations CPIAUCSL --limit 3`. BLS observations can be pulled with `python -m app.cli bls-timeseries CUUR0000SA0 --start-year 2026 --end-year 2026 --limit 3`. GDELT discovery candidates can be pulled with `python -m app.cli gdelt-search "NVDA export controls" --limit 5 --timespan 24h`. Rights-reviewed market reaction context can be imported with `python -m app.cli market-csv ..\data\market-reactions.csv --source-name "Licensed desk export"`.

Live ingestion still needs normal provider care: SEC requests require a real declared `SEC_USER_AGENT`, FRED requests require `FRED_API_KEY`, BLS registered keys can be supplied with `BLS_API_KEY` for better limits, and source/provider terms must be reviewed before commercial reuse.

GDELT items are discovery-only. They can help find candidate stories, but they do not satisfy the primary-source gate without an official or first-party source.

Market CSV rows are enrichment only. The importer expects a `ticker` column and accepts optional columns including `date`, `published_at`, `price_change_pct`, `volume_vs_20d`, `mention_velocity`, `novelty_score`, `sector_etf`, `event_key`, `title`, `summary`, `canonical_url`, `source_name`, `license_notes`, `tickers`, and `themes`. Imported rows default to provider redistribution review until the data license is cleared.

Open `preview.html` in an exported story folder to review the vertical package, source trail, QA gates, chart, and storyboard together before rendering a final MP4.

RSS ingestion writes source snapshots to an append-only local archive at `.runtime/source_archive.jsonl` by default. Set `MARKET_SIGNAL_SOURCE_ARCHIVE` to move it. The archive is local audit data and should not be committed.

Source-terms reviews are appended to `.runtime/source_terms.jsonl` by default. Set `MARKET_SIGNAL_SOURCE_TERMS` to move it. Terms reviews can mark a source as `approved_publish`, `internal_only`, `prohibited`, or `needs_review`; rights reports use the latest review for each source/provider.

The dashboard includes an editor decision panel for approve, hold, revise, or archive decisions with notes. Decisions are appended to a local JSONL ledger by default at `.runtime/decisions.jsonl`; production should move this ledger into Postgres with user identity and immutable audit controls.

Each generated package includes an editorial format, style variant, and angle. This keeps recurring videos from collapsing into one repeated headline-summary template.

`claims.json` is the claim-level review checklist. It separates source-backed claims from claims that still require editor verification, such as market-data numbers, causal framing, and chart choices.

`rights_report.json` summarizes source posture: official, first-party, provider-review, missing notes, or unknown. Use it to keep raw market-data redistribution and article-reuse questions visible before approval.

`source_terms.jsonl` records source/provider terms reviews. A current `approved_publish` review can move a provider source from provider-review to licensed; a `prohibited` review blocks approval.

`platform_readiness.json` checks whether a draft has enough original framing, visual transformation, caveat language, and human judgment to avoid feeling like commodity headline reuse.

`approval_checklist.json` is the final pre-publish gate. Blocking checks prevent approval; warning-level packages require editor notes before approval can be recorded.

Primary-source overrides are available for rare editor-reviewed exceptions. They require an editor, a reason, and an evidence URL, and they turn the primary-source gate into a warning rather than a pass. Overrides are appended to `.runtime/overrides.jsonl` by default.

## Source posture

The MVP treats official and first-party sources as the highest authority layer: SEC, Fed, BLS, FRED, issuer IR feeds, and official press releases. Broad news discovery, social buzz, and market data providers are enrichment layers, not the only source of truth.

The system stores license notes and source provenance on each item because "an API returned JSON" is not the same thing as redistribution rights.

## Editorial guardrails

Every generated draft runs through QA gates:

- Primary-source traceability.
- No personalized advice language.
- Rights and copyright hygiene.
- Original explanation, not headline reuse.
- Platform readiness for Shorts/Reels style distribution.
- Editorial format variation so recurring packages do not sound mass-produced.
- Approval checklist with editor notes required for warning-level packages.
- One clear chart idea.
- Caveat or uncertainty note.
- Disclosure readiness for sponsors, affiliates, or paid promotions.

This is an engineering workflow, not legal advice. Commercial use still needs provider-specific terms review.

## Repo status

This is a working scaffold intended to become the first production MVP. The next build steps are persistent storage, scheduled ingestion, real provider adapters, Remotion render templates, and editor authentication.
