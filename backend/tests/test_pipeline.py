from __future__ import annotations

import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

from app.exporter import export_story_slate
from app.ingest.catalog import load_source_catalog
from app.models import SourceItem
from app.pipeline.compliance import run_qa
from app.pipeline.scoring import build_story_candidates
from app.pipeline.script_writer import generate_video_package
from app.store import EditorialStore


class PipelineTests(unittest.TestCase):
    def test_sample_data_builds_ranked_story_slate(self) -> None:
        store = EditorialStore(Path(__file__).parents[1] / "app" / "data" / "sample_sources.json")

        stories = store.stories

        self.assertGreaterEqual(len(stories), 4)
        self.assertGreater(stories[0].scores["story_score"], 0.65)
        self.assertTrue(stories[0].source_trail)

    def test_generated_package_keeps_editorial_guardrails(self) -> None:
        store = EditorialStore(Path(__file__).parents[1] / "app" / "data" / "sample_sources.json")
        story = store.stories[0]

        package = generate_video_package(story)
        qa = run_qa(story, package)

        self.assertIn("This is not a recommendation", package.script_60s)
        self.assertNotIn("you should buy", package.script_60s.lower())
        self.assertNotEqual(qa["status"], "blocked")

    def test_primary_source_scores_above_discovery_only(self) -> None:
        official = SourceItem(
            id="official",
            source_type="sec_filing",
            source_name="SEC",
            retrieved_at="2026-06-27T12:00:00Z",
            published_at="2026-06-27T12:00:00Z",
            canonical_url="https://example.com/official",
            title="Sample 8-K for NVDA",
            summary="Official sample filing.",
            tickers=["NVDA"],
            themes=["filings"],
            event_key="same-event",
            source_authority=0.98,
            primary_source=True,
            license_notes="Sample official source.",
            market={"price_change_pct": 2.0, "volume_vs_20d": 1.5, "novelty_score": 0.7},
        )
        discovery = SourceItem(
            id="discovery",
            source_type="news_discovery",
            source_name="Discovery",
            retrieved_at="2026-06-27T12:00:00Z",
            published_at="2026-06-27T12:00:00Z",
            canonical_url="https://example.com/discovery",
            title="News item says NVDA moved",
            summary="Discovery-only sample.",
            tickers=["NVDA"],
            themes=["filings"],
            event_key="same-event",
            source_authority=0.45,
            primary_source=False,
            license_notes="Discovery only.",
            market={"price_change_pct": 2.0, "volume_vs_20d": 1.5, "novelty_score": 0.7},
        )

        story = build_story_candidates([discovery, official])[0]

        self.assertTrue(story.primary_evidence)
        self.assertGreater(story.scores["source_authority"], 0.6)

    def test_source_catalog_contains_official_feeds(self) -> None:
        feeds = load_source_catalog(Path(__file__).parents[1] / "app" / "data" / "source_feeds.json")

        feed_ids = {feed.id for feed in feeds}

        self.assertIn("sec_current_filings", feed_ids)
        self.assertIn("fed_monetary_policy", feed_ids)
        self.assertIn("bls_employment_situation", feed_ids)

    def test_export_story_slate_writes_editor_files(self) -> None:
        store = EditorialStore(Path(__file__).parents[1] / "app" / "data" / "sample_sources.json")

        with TemporaryDirectory() as temp_dir:
            result = export_story_slate(store.stories, Path(temp_dir), limit=2)

            self.assertTrue(Path(result["slate"]).exists())
            self.assertEqual(len(result["packages"]), 2)
            for package_files in result["packages"]:
                self.assertTrue(Path(package_files["story"]).exists())
                self.assertTrue(Path(package_files["package"]).exists())
                self.assertTrue(Path(package_files["qa"]).exists())
                self.assertTrue(Path(package_files["manifest"]).exists())
                self.assertIn("editor_brief.md", package_files["brief"])


if __name__ == "__main__":
    unittest.main()
