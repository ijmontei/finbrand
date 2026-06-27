# Market Signal Studio

Market Signal Studio is a rights-aware editorial engine for short-form finance content. It is built around the stronger version of the idea: automated signal detection, source-grounded research packets, original commentary, visual explanation, and human approval before anything gets published.

The first product lane is:

> Why stocks moved today, explained with data instead of vibes.

## What is included

- Python editorial engine for source normalization, entity mapping, story clustering, ranking, script drafting, chart ideas, and compliance QA.
- FastAPI backend exposing story, package, RSS ingest, and QA endpoints.
- React dashboard for reviewing the story slate, source trail, scoring rationale, generated script, and publishing gates.
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

## Source posture

The MVP treats official and first-party sources as the highest authority layer: SEC, Fed, BLS, FRED, issuer IR feeds, and official press releases. Broad news discovery, social buzz, and market data providers are enrichment layers, not the only source of truth.

The system stores license notes and source provenance on each item because "an API returned JSON" is not the same thing as redistribution rights.

## Editorial guardrails

Every generated draft runs through QA gates:

- Primary-source traceability.
- No personalized advice language.
- Rights and copyright hygiene.
- Original explanation, not headline reuse.
- One clear chart idea.
- Caveat or uncertainty note.
- Disclosure readiness for sponsors, affiliates, or paid promotions.

This is an engineering workflow, not legal advice. Commercial use still needs provider-specific terms review.

## Repo status

This is a working scaffold intended to become the first production MVP. The next build steps are persistent storage, scheduled ingestion, real provider adapters, Remotion render templates, and editor authentication.

