from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

from app.approval import build_approval_checklist
from app.decision_ledger import DecisionLedger
from app.models import EditorialDecision, SourceItem, StoryCandidate, VideoPackage
from app.pipeline.compliance import run_qa
from app.pipeline.scoring import build_story_candidates
from app.pipeline.script_writer import generate_video_package
from app.source_archive import SourceArchive


class EditorialStore:
    def __init__(
        self,
        sample_path: Path | None = None,
        decision_ledger: DecisionLedger | None = None,
        source_archive: SourceArchive | None = None,
    ) -> None:
        self.sample_path = sample_path or Path(__file__).parent / "data" / "sample_sources.json"
        self.decision_ledger = decision_ledger or DecisionLedger()
        self.source_archive = source_archive or SourceArchive()
        self.last_source_archive_summary: dict[str, object] = self.source_archive.summary()
        self.source_items: list[SourceItem] = self._load_sample_items()
        self.stories: list[StoryCandidate] = []
        self.packages: dict[str, VideoPackage] = {}
        self.decisions: dict[str, EditorialDecision] = self.decision_ledger.load_latest()
        self.refresh_stories()

    def refresh_stories(self) -> list[StoryCandidate]:
        self.stories = build_story_candidates(self.source_items)
        return self.stories

    def list_stories(self) -> list[dict[str, object]]:
        return [story.to_dict() for story in self.stories]

    def get_story(self, story_id: str) -> StoryCandidate:
        for story in self.stories:
            if story.story_id == story_id:
                return story
        raise KeyError(story_id)

    def get_or_generate_package(self, story_id: str) -> VideoPackage:
        if story_id not in self.packages:
            self.packages[story_id] = generate_video_package(self.get_story(story_id))
        return self.packages[story_id]

    def get_qa(self, story_id: str) -> dict[str, object]:
        story = self.get_story(story_id)
        package = self.get_or_generate_package(story_id)
        return run_qa(story, package)

    def get_decision(self, story_id: str) -> dict[str, object]:
        self.get_story(story_id)
        decision = self.decisions.get(story_id)
        if decision:
            return decision.to_dict()
        return self._pending_decision(story_id)

    def record_decision(self, story_id: str, decision: str, editor: str, notes: str) -> dict[str, object]:
        story = self.get_story(story_id)
        package = self.get_or_generate_package(story_id)
        qa = self.get_qa(story_id)
        allowed = {"approve", "hold", "revise", "archive"}
        if decision not in allowed:
            raise ValueError(f"decision must be one of: {', '.join(sorted(allowed))}")
        clean_notes = notes.strip()
        if decision == "approve":
            approval = build_approval_checklist(story, package)
            if approval["status"] == "blocked":
                raise ValueError("cannot approve a package with blocking approval checks")
            if approval["notes_required"] and not clean_notes:
                raise ValueError("approval notes are required while approval checks need review")
        record = EditorialDecision(
            story_id=story_id,
            decision=decision,
            editor=editor.strip() or "editor",
            notes=clean_notes,
            decided_at=datetime.now(timezone.utc).isoformat(),
            qa_status=str(qa["status"]),
            story_score=float(story.scores["story_score"]),
        )
        self.decisions[story_id] = record
        self.decision_ledger.append(record)
        return record.to_dict()

    def ingest_rss(
        self,
        feed_url: str,
        source_name: str,
        source_type: str,
        license_notes: str | None = None,
    ) -> list[dict[str, object]]:
        from app.ingest.rss import fetch_rss_feed

        items = fetch_rss_feed(feed_url, source_name, source_type, license_notes=license_notes)
        self.source_items.extend(items)
        self.last_source_archive_summary = self.source_archive.append_many(
            items,
            context={
                "ingest_method": "rss",
                "feed_url": feed_url,
                "source_name": source_name,
                "source_type": source_type,
            },
        )
        self.refresh_stories()
        return [item.to_dict() for item in items]

    def ingest_sec_submissions(
        self,
        cik: str,
        limit: int = 10,
        user_agent: str | None = None,
    ) -> list[dict[str, object]]:
        from app.ingest.sec import fetch_sec_submissions

        items = fetch_sec_submissions(cik, limit=limit, user_agent=user_agent)
        self.source_items.extend(items)
        self.last_source_archive_summary = self.source_archive.append_many(
            items,
            context={
                "ingest_method": "sec_submissions",
                "cik": cik,
                "limit": limit,
            },
        )
        self.refresh_stories()
        return [item.to_dict() for item in items]

    def ingest_fred_observations(
        self,
        series_id: str,
        limit: int = 3,
        api_key: str | None = None,
    ) -> list[dict[str, object]]:
        from app.ingest.fred import fetch_fred_observations

        items = fetch_fred_observations(series_id, limit=limit, api_key=api_key)
        self.source_items.extend(items)
        self.last_source_archive_summary = self.source_archive.append_many(
            items,
            context={
                "ingest_method": "fred_observations",
                "series_id": series_id.upper(),
                "limit": limit,
            },
        )
        self.refresh_stories()
        return [item.to_dict() for item in items]

    def ingest_bls_timeseries(
        self,
        series_id: str,
        start_year: int,
        end_year: int,
        limit: int = 3,
        api_key: str | None = None,
    ) -> list[dict[str, object]]:
        from app.ingest.bls import fetch_bls_timeseries

        items = fetch_bls_timeseries(series_id, start_year, end_year, limit=limit, api_key=api_key)
        self.source_items.extend(items)
        self.last_source_archive_summary = self.source_archive.append_many(
            items,
            context={
                "ingest_method": "bls_timeseries",
                "series_id": series_id.upper(),
                "start_year": start_year,
                "end_year": end_year,
                "limit": limit,
            },
        )
        self.refresh_stories()
        return [item.to_dict() for item in items]

    def ingest_gdelt_articles(
        self,
        query: str,
        limit: int = 10,
        timespan: str = "24h",
    ) -> list[dict[str, object]]:
        from app.ingest.gdelt import fetch_gdelt_articles

        items = fetch_gdelt_articles(query, limit=limit, timespan=timespan)
        self.source_items.extend(items)
        self.last_source_archive_summary = self.source_archive.append_many(
            items,
            context={
                "ingest_method": "gdelt_articles",
                "query": query,
                "timespan": timespan,
                "limit": limit,
                "publish_posture": "discovery_only",
            },
        )
        self.refresh_stories()
        return [item.to_dict() for item in items]

    def ingest_market_csv(
        self,
        path: Path | str,
        source_name: str | None = None,
    ) -> list[dict[str, object]]:
        from app.ingest.market_csv import DEFAULT_SOURCE_NAME, load_market_csv

        provider_name = source_name or DEFAULT_SOURCE_NAME
        items = load_market_csv(path, source_name=provider_name)
        self.source_items.extend(items)
        self.last_source_archive_summary = self.source_archive.append_many(
            items,
            context={
                "ingest_method": "market_csv",
                "csv_path": str(path),
                "source_name": provider_name,
                "publish_posture": "provider_review",
            },
        )
        self.refresh_stories()
        return [item.to_dict() for item in items]

    def source_archive_summary(self) -> dict[str, object]:
        return self.source_archive.summary()

    def _load_sample_items(self) -> list[SourceItem]:
        with self.sample_path.open("r", encoding="utf-8") as handle:
            raw_items = json.load(handle)
        return [SourceItem(**item) for item in raw_items]

    def _pending_decision(self, story_id: str) -> dict[str, object]:
        story = self.get_story(story_id)
        qa = self.get_qa(story_id)
        return {
            "story_id": story_id,
            "decision": "pending",
            "editor": "",
            "notes": "",
            "decided_at": None,
            "qa_status": qa["status"],
            "story_score": story.scores["story_score"],
        }
