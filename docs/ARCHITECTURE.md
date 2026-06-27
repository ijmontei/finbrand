# Architecture

## Current MVP

```mermaid
flowchart LR
    A["Sample source records"] --> B["Normalizer"]
    A --> I["Local source archive"]
    B --> C["Entity and theme mapping"]
    C --> D["Story clustering"]
    D --> E["Scoring engine"]
    E --> F["Draft package generator"]
    F --> G["Compliance QA"]
    G --> H["React editorial dashboard"]
    G --> J["Daily brief export"]
    G --> K["50-piece content batch export"]
```

## Production target

```mermaid
flowchart LR
    A["Schedulers"] --> B["Ingestion workers"]
    B --> C["Official feeds and APIs"]
    B --> D["Discovery feeds"]
    B --> E["Market data providers"]
    C --> F["Raw source archive"]
    D --> F
    E --> F
    F --> G["Canonical database"]
    G --> H["Novelty and dedupe index"]
    G --> I["Story scorer"]
    I --> J["Editorial package"]
    J --> K["QA dashboard"]
    K --> L["Render queue"]
```

## Backend modules

- `app.models`: dataclass schemas for source items, story candidates, packages, and QA gates.
- `app.approval`: final approval checklist combining QA, claims, rights, and platform readiness.
- `app.content_batch`: 50-piece draft launch-batch builder with platform and editorial-lens rotation.
- `app.newsletter`: owned-audience daily brief builder and exporter.
- `app.overrides`: append-only editor override ledger and validation helpers.
- `app.ingest.bls`: BLS time-series adapter for official labor and inflation observations.
- `app.ingest.gdelt`: GDELT article discovery adapter that produces non-primary candidates.
- `app.ingest.market_csv`: rights-aware CSV adapter for licensed market reaction context.
- `app.pipeline.entity_mapping`: watchlist, source authority defaults, ticker and theme inference.
- `app.pipeline.scoring`: clustering and weighted story score.
- `app.pipeline.script_writer`: deterministic editorial package generator with format and style variation.
- `app.pipeline.compliance`: publish-readiness gates.
- `app.platform`: platform originality and reused-content readiness report.
- `app.source_archive`: append-only local JSONL archive for ingested source snapshots.
- `app.source_terms`: append-only source/provider terms review ledger.
- `app.ingest.fred`: FRED observations adapter for official macro series.
- `app.ingest.rss`: RSS ingestion adapter.
- `app.ingest.sec`: SEC EDGAR submissions adapter.
- `app.store`: in-memory MVP store.
- `app.main`: FastAPI endpoints.

## API surface

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Health check |
| `GET` | `/api/stories` | Ranked story slate |
| `POST` | `/api/stories/refresh` | Recompute slate |
| `GET` | `/api/stories/{story_id}` | Story detail |
| `POST` | `/api/stories/{story_id}/package` | Generate draft package |
| `GET` | `/api/stories/{story_id}/qa` | QA result |
| `GET` | `/api/stories/{story_id}/claims` | Claim-level source and editor-verification checklist |
| `GET` | `/api/stories/{story_id}/rights` | Source-rights and redistribution review report |
| `GET` | `/api/stories/{story_id}/platform-readiness` | Platform originality and reused-content readiness report |
| `GET` | `/api/stories/{story_id}/approval` | Final pre-publish approval checklist |
| `GET` | `/api/stories/{story_id}/publish-packet` | Approval-gated manual publishing packet |
| `GET` | `/api/content-batch?count=50` | Draft content batch preview for launch or weekly production planning |
| `GET` | `/api/stories/{story_id}/overrides` | Active editor overrides for a story |
| `POST` | `/api/stories/{story_id}/overrides` | Record an audited editor override |
| `GET` | `/api/stories/{story_id}/decision` | Current editorial decision |
| `POST` | `/api/stories/{story_id}/decision` | Record approve, hold, revise, or archive decision |
| `GET` | `/api/stories/{story_id}/chart.svg` | Generated editorial signal chart |
| `GET` | `/api/stories/{story_id}/storyboard` | 60-second vertical render plan |
| `GET` | `/api/stories/{story_id}/captions.srt` | Draft subtitle file |
| `GET` | `/api/stories/{story_id}/preview.html` | Openable vertical review preview |
| `GET` | `/api/sources/catalog` | Configured official source feeds |
| `POST` | `/api/sources/rss` | Ingest an RSS feed |
| `GET` | `/api/sources/archive` | Local source archive status |
| `GET` | `/api/source-terms` | Latest source/provider terms reviews |
| `POST` | `/api/source-terms` | Record a source/provider terms review |

## CLI surface

| Command | Purpose |
| --- | --- |
| `python -m app.cli catalog` | List configured official source feeds |
| `python -m app.cli slate --limit 5` | Print the ranked story slate |
| `python -m app.cli package STORY_ID` | Generate one story package |
| `python -m app.cli qa STORY_ID` | Run QA for one story |
| `python -m app.cli publish-packet STORY_ID --output-dir exports/publish` | Write approval-gated manual publishing files |
| `python -m app.cli content-batch --count 50 --output-dir exports/content-batch` | Write 50 draft content pieces plus a batch index |
| `python -m app.cli export --output-dir exports/latest --limit 5` | Write editor briefs, manifests, QA, and package JSON |
| `python -m app.cli newsletter --output-dir exports/newsletter --limit 3` | Write `daily_brief.md` and `daily_brief.json` |
| `python -m app.cli ingest-feed FEED_ID` | Pull one configured RSS feed |
| `python -m app.cli sec-submissions CIK --limit 5` | Pull recent SEC submissions for one CIK |
| `python -m app.cli fred-observations SERIES_ID --limit 3` | Pull recent FRED observations for one macro series |
| `python -m app.cli bls-timeseries SERIES_ID --start-year YYYY --end-year YYYY --limit 3` | Pull recent BLS time-series observations |
| `python -m app.cli gdelt-search QUERY --limit 10 --timespan 24h` | Pull GDELT article discovery candidates |
| `python -m app.cli market-csv PATH --source-name PROVIDER` | Import provider-review market reaction context from CSV |
| `python -m app.cli source-terms` | List reviewed source/provider terms |
| `python -m app.cli review-source-terms SOURCE --source-type TYPE --review-status STATUS ...` | Record a provider/source terms review |
| `python -m app.cli override-primary-source STORY_ID --reason TEXT --evidence-url URL` | Record an audited primary-source exception |
| `python -m app.cli archive-status` | Show local source archive path and record count |

## Storage path

The MVP uses an in-memory store seeded from JSON. The next version should add Postgres tables:

- `source_items`
- `entities`
- `story_clusters`
- `story_candidates`
- `scripts`
- `qa_runs`
- `asset_manifests`
- `publish_jobs`
- `content_batches`

Add `jsonb` for raw provider payloads and `pgvector` later for novelty and dedupe.

## Audit trail

The MVP writes ingested source snapshots to an append-only JSONL archive. By default this lives at `.runtime/source_archive.jsonl`, or at `MARKET_SIGNAL_SOURCE_ARCHIVE` when configured. Each record includes the normalized source item, source URL, provenance, and ingest context.

The MVP also writes editorial decisions to an append-only JSONL ledger. By default this lives at `.runtime/decisions.jsonl`, or at `MARKET_SIGNAL_DECISION_LEDGER` when configured. The store loads the latest decision per story on startup, so approvals, holds, revision notes, and archive decisions survive local restarts.

Primary-source overrides are written to an append-only JSONL ledger at `.runtime/overrides.jsonl`, or at `MARKET_SIGNAL_OVERRIDE_LEDGER` when configured. Overrides are active exception records with editor, reason, evidence URL, and timestamp; they turn the primary-source gate into a warning, not a pass.

Source/provider terms reviews are written to an append-only JSONL ledger at `.runtime/source_terms.jsonl`, or at `MARKET_SIGNAL_SOURCE_TERMS` when configured. The latest review for a source/provider is applied to rights reports, QA gates, daily briefs, and exported editor packages.

Production should promote this into Postgres with:

- immutable raw source snapshots
- immutable append-only decision events
- immutable append-only override events
- immutable append-only source-terms review events
- authenticated editor identity
- old and new state
- QA snapshot
- source trail snapshot
- publish job linkage
