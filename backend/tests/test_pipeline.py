from __future__ import annotations

import unittest
from dataclasses import replace
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch

from app.approval import build_approval_checklist
from app.charts import render_signal_chart_svg
from app.claims import build_claim_checklist
from app.decision_ledger import DecisionLedger
from app.exporter import export_publish_packet, export_story_slate
from app.ingest.bls import bls_timeseries_payload_to_source_items
from app.ingest.catalog import load_source_catalog
from app.ingest.fred import fred_observations_payload_to_source_items, require_fred_api_key
from app.ingest.gdelt import gdelt_payload_to_source_items
from app.ingest.market_csv import market_csv_rows_to_source_items
from app.ingest.sec import require_sec_user_agent, submissions_payload_to_source_items
from app.models import SourceItem
from app.newsletter import build_daily_brief, export_daily_brief, render_daily_brief_markdown
from app.overrides import OverrideLedger
from app.pipeline.compliance import run_qa
from app.pipeline.scoring import build_story_candidates
from app.pipeline.script_writer import generate_video_package
from app.platform import build_platform_readiness
from app.render_plan import build_storyboard, generate_srt, render_preview_html
from app.rights import build_rights_report
from app.source_archive import SourceArchive
from app.source_terms import SourceTermsLedger
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
        self.assertTrue(package.format_key)
        self.assertTrue(package.format_name)
        self.assertTrue(package.editorial_angle)
        self.assertIn("editorial_format", package.asset_manifest)
        self.assertNotEqual(qa["status"], "blocked")

    def test_story_slate_uses_multiple_editorial_formats(self) -> None:
        store = EditorialStore(Path(__file__).parents[1] / "app" / "data" / "sample_sources.json")

        formats = {generate_video_package(story).format_key for story in store.stories}

        self.assertGreaterEqual(len(formats), 3)

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

    def test_sec_submissions_payload_builds_primary_source_items(self) -> None:
        items = submissions_payload_to_source_items(_sample_sec_submissions_payload(), limit=1)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].source_type, "sec_filing")
        self.assertTrue(items[0].primary_source)
        self.assertIn("AAPL", items[0].tickers)
        self.assertIn("0000320193", items[0].ciks)
        self.assertIn("sec.gov/Archives", items[0].canonical_url)
        self.assertEqual(items[0].provenance["form"], "10-Q")

    def test_sec_user_agent_is_required(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValueError):
                require_sec_user_agent()

        with patch.dict("os.environ", {"SEC_USER_AGENT": "Market Signal Studio test contact@example.com"}):
            self.assertIn("Market Signal Studio", require_sec_user_agent())

    def test_store_archives_sec_submissions(self) -> None:
        with TemporaryDirectory() as temp_dir:
            archive = SourceArchive(Path(temp_dir) / "source_archive.jsonl")
            ledger = DecisionLedger(Path(temp_dir) / "decisions.jsonl")
            item = submissions_payload_to_source_items(_sample_sec_submissions_payload(), limit=1)[0]
            store = EditorialStore(
                Path(__file__).parents[1] / "app" / "data" / "sample_sources.json",
                decision_ledger=ledger,
                source_archive=archive,
            )

            with patch("app.ingest.sec.fetch_sec_submissions", return_value=[item]):
                result = store.ingest_sec_submissions("320193", limit=1, user_agent="test contact@example.com")

            self.assertEqual(len(result), 1)
            self.assertEqual(store.last_source_archive_summary["count"], 1)
            self.assertEqual(archive.read_all()[0]["context"]["ingest_method"], "sec_submissions")

    def test_fred_observations_payload_builds_macro_source_items(self) -> None:
        items = fred_observations_payload_to_source_items("CPIAUCSL", _sample_fred_observations_payload(), limit=2)

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].source_type, "fred_series")
        self.assertTrue(items[0].primary_source)
        self.assertIn("inflation", items[0].themes)
        self.assertEqual(items[0].market["series_value"], 318.1)
        self.assertIn("fred.stlouisfed.org/series/CPIAUCSL", items[0].canonical_url)

    def test_fred_api_key_is_required(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValueError):
                require_fred_api_key()

        with patch.dict("os.environ", {"FRED_API_KEY": "test-key"}):
            self.assertEqual(require_fred_api_key(), "test-key")

    def test_store_archives_fred_observations(self) -> None:
        with TemporaryDirectory() as temp_dir:
            archive = SourceArchive(Path(temp_dir) / "source_archive.jsonl")
            ledger = DecisionLedger(Path(temp_dir) / "decisions.jsonl")
            item = fred_observations_payload_to_source_items("CPIAUCSL", _sample_fred_observations_payload(), limit=1)[0]
            store = EditorialStore(
                Path(__file__).parents[1] / "app" / "data" / "sample_sources.json",
                decision_ledger=ledger,
                source_archive=archive,
            )

            with patch("app.ingest.fred.fetch_fred_observations", return_value=[item]):
                result = store.ingest_fred_observations("CPIAUCSL", limit=1, api_key="test-key")

            self.assertEqual(len(result), 1)
            self.assertEqual(store.last_source_archive_summary["count"], 1)
            self.assertEqual(archive.read_all()[0]["context"]["ingest_method"], "fred_observations")

    def test_bls_timeseries_payload_builds_primary_source_items(self) -> None:
        items = bls_timeseries_payload_to_source_items(_sample_bls_timeseries_payload(), limit=2)

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].source_type, "bls_release")
        self.assertTrue(items[0].primary_source)
        self.assertIn("inflation", items[0].themes)
        self.assertEqual(items[0].market["series_value"], 318.1)
        self.assertIn("data.bls.gov/timeseries/CUUR0000SA0", items[0].canonical_url)

    def test_store_archives_bls_timeseries(self) -> None:
        with TemporaryDirectory() as temp_dir:
            archive = SourceArchive(Path(temp_dir) / "source_archive.jsonl")
            ledger = DecisionLedger(Path(temp_dir) / "decisions.jsonl")
            item = bls_timeseries_payload_to_source_items(_sample_bls_timeseries_payload(), limit=1)[0]
            store = EditorialStore(
                Path(__file__).parents[1] / "app" / "data" / "sample_sources.json",
                decision_ledger=ledger,
                source_archive=archive,
            )

            with patch("app.ingest.bls.fetch_bls_timeseries", return_value=[item]):
                result = store.ingest_bls_timeseries("CUUR0000SA0", start_year=2026, end_year=2026, limit=1)

            self.assertEqual(len(result), 1)
            self.assertEqual(store.last_source_archive_summary["count"], 1)
            self.assertEqual(archive.read_all()[0]["context"]["ingest_method"], "bls_timeseries")

    def test_gdelt_payload_builds_discovery_only_items(self) -> None:
        items = gdelt_payload_to_source_items(_sample_gdelt_payload(), query="NVDA export controls", limit=1)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].source_type, "news_discovery")
        self.assertFalse(items[0].primary_source)
        self.assertIn("NVDA", items[0].tickers)
        self.assertIn("discovery", items[0].license_notes.lower())
        self.assertEqual(items[0].provenance["query"], "NVDA export controls")

    def test_gdelt_only_story_requires_primary_source_review(self) -> None:
        story = build_story_candidates(
            gdelt_payload_to_source_items(_sample_gdelt_payload(), query="NVDA export controls", limit=1)
        )[0]
        package = generate_video_package(story)
        qa = run_qa(story, package)
        rights = build_rights_report(story)

        self.assertIn("needs_primary_source_review", story.risk_flags)
        self.assertEqual(qa["status"], "blocked")
        self.assertEqual(rights["status"], "needs_review")

    def test_primary_source_override_downgrades_block_to_warning(self) -> None:
        story = build_story_candidates(
            gdelt_payload_to_source_items(_sample_gdelt_payload(), query="NVDA export controls", limit=1)
        )[0]
        package = generate_video_package(story)
        override = {
            "story_id": story.story_id,
            "override_type": "primary_source",
            "editor": "editor",
            "reason": "Official source is unavailable; editor verified the context against internal notes.",
            "evidence_url": "internal://editorial/source-review/1",
            "created_at": "2026-06-27T13:00:00+00:00",
            "active": True,
        }

        qa = run_qa(story, package, editorial_overrides=[override])
        claims = build_claim_checklist(story, package, editorial_overrides=[override])
        approval = build_approval_checklist(story, package, editorial_overrides=[override])

        self.assertEqual(qa["status"], "needs_review")
        self.assertTrue(
            any(
                gate["name"] == "Primary-source traceability" and gate["status"] == "warn"
                for gate in qa["gates"]
            )
        )
        self.assertEqual(claims["status"], "needs_review")
        self.assertTrue(approval["can_approve"])
        self.assertTrue(approval["notes_required"])
        self.assertEqual(approval["editorial_overrides"][0]["override_type"], "primary_source")

    def test_store_archives_gdelt_discovery_items(self) -> None:
        with TemporaryDirectory() as temp_dir:
            archive = SourceArchive(Path(temp_dir) / "source_archive.jsonl")
            ledger = DecisionLedger(Path(temp_dir) / "decisions.jsonl")
            item = gdelt_payload_to_source_items(_sample_gdelt_payload(), query="NVDA export controls", limit=1)[0]
            store = EditorialStore(
                Path(__file__).parents[1] / "app" / "data" / "sample_sources.json",
                decision_ledger=ledger,
                source_archive=archive,
            )

            with patch("app.ingest.gdelt.fetch_gdelt_articles", return_value=[item]):
                result = store.ingest_gdelt_articles("NVDA export controls", limit=1, timespan="24h")

            self.assertEqual(len(result), 1)
            self.assertEqual(store.last_source_archive_summary["count"], 1)
            self.assertEqual(archive.read_all()[0]["context"]["ingest_method"], "gdelt_articles")
            self.assertEqual(archive.read_all()[0]["context"]["publish_posture"], "discovery_only")

    def test_market_csv_rows_build_provider_review_items(self) -> None:
        rows = [
            {
                "ticker": "NVDA",
                "date": "2026-06-27",
                "price_change_pct": "-4.2",
                "volume_vs_20d": "2.1",
                "mention_velocity": "64",
                "novelty_score": "0.84",
                "sector_etf": "SMH",
                "event_key": "sample-ai-supply-chain",
                "summary": "Market data signal points to semiconductor weakness.",
            }
        ]

        items = market_csv_rows_to_source_items(rows, source_name="Licensed desk export")

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].source_type, "market_data")
        self.assertFalse(items[0].primary_source)
        self.assertIn("Provider redistribution review", items[0].license_notes)
        self.assertIn("NVDA", items[0].tickers)
        self.assertIn("SMH", items[0].tickers)
        self.assertEqual(items[0].market["price_change_pct"], -4.2)
        self.assertEqual(items[0].market["volume_vs_20d"], 2.1)
        self.assertEqual(items[0].provenance["publish_posture"], "provider_review")

    def test_market_csv_enriches_primary_story_but_keeps_rights_review(self) -> None:
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
            market={"price_change_pct": 0.0, "volume_vs_20d": 1.0, "novelty_score": 0.7},
        )
        market = market_csv_rows_to_source_items(
            [
                {
                    "ticker": "NVDA",
                    "published_at": "2026-06-27T12:04:00Z",
                    "price_change_pct": "-5.4",
                    "volume_vs_20d": "3.2",
                    "mention_velocity": "80",
                    "event_key": "same-event",
                }
            ]
        )[0]

        story = build_story_candidates([official, market])[0]
        rights = build_rights_report(story)

        self.assertEqual(story.metrics["price_change_pct"], -5.4)
        self.assertEqual(story.metrics["volume_vs_20d"], 3.2)
        self.assertIn("market_data_rights_review", story.risk_flags)
        self.assertEqual(rights["summary"]["provider_review"], 1)
        self.assertEqual(rights["status"], "needs_review")

    def test_source_terms_review_can_license_provider_source(self) -> None:
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
            market={"price_change_pct": 0.0, "volume_vs_20d": 1.0, "novelty_score": 0.7},
        )
        market = market_csv_rows_to_source_items(
            [
                {
                    "ticker": "NVDA",
                    "published_at": "2026-06-27T12:04:00Z",
                    "price_change_pct": "-5.4",
                    "volume_vs_20d": "3.2",
                    "event_key": "same-event",
                    "source_name": "Licensed desk export",
                }
            ]
        )[0]
        story = build_story_candidates([official, market])[0]

        rights = build_rights_report(
            story,
            source_terms=[
                {
                    "source_name": "Licensed desk export",
                    "source_type": "market_data",
                    "review_status": "approved_publish",
                    "terms_url": "internal://terms/market-data",
                    "reviewed_by": "editor",
                    "reviewed_at": "2026-06-27T12:00:00+00:00",
                    "allowed_use": "May publish derived market reaction values with attribution.",
                    "restrictions": "No raw quote feed redistribution.",
                    "expires_at": "",
                }
            ],
        )

        self.assertEqual(rights["summary"]["licensed"], 1)
        self.assertEqual(rights["summary"]["provider_review"], 0)
        self.assertTrue(any(source["posture"] == "licensed" for source in rights["sources"]))

    def test_prohibited_source_terms_block_rights_report(self) -> None:
        story = build_story_candidates(
            gdelt_payload_to_source_items(_sample_gdelt_payload(), query="NVDA export controls", limit=1)
        )[0]

        rights = build_rights_report(
            story,
            source_terms=[
                {
                    "source_name": "GDELT DOC: Example Markets",
                    "source_type": "news_discovery",
                    "review_status": "prohibited",
                    "terms_url": "internal://terms/news-discovery",
                    "reviewed_by": "editor",
                    "reviewed_at": "2026-06-27T12:00:00+00:00",
                    "allowed_use": "Do not use in published outputs.",
                    "restrictions": "Provider terms prohibit this use.",
                    "expires_at": "",
                }
            ],
        )

        self.assertEqual(rights["status"], "blocked")
        self.assertEqual(rights["summary"]["prohibited"], 1)
        self.assertTrue(any(source["review_action"] == "Remove or replace this source before approval." for source in rights["sources"]))

    def test_store_archives_market_csv_items(self) -> None:
        with TemporaryDirectory() as temp_dir:
            archive = SourceArchive(Path(temp_dir) / "source_archive.jsonl")
            ledger = DecisionLedger(Path(temp_dir) / "decisions.jsonl")
            csv_path = Path(temp_dir) / "market.csv"
            csv_path.write_text(
                "ticker,date,price_change_pct,volume_vs_20d,mention_velocity,sector_etf\n"
                "NVDA,2026-06-27,-4.2,2.1,64,SMH\n",
                encoding="utf-8",
            )
            store = EditorialStore(
                Path(__file__).parents[1] / "app" / "data" / "sample_sources.json",
                decision_ledger=ledger,
                source_archive=archive,
            )

            result = store.ingest_market_csv(csv_path, source_name="Licensed desk export")

            self.assertEqual(len(result), 1)
            self.assertEqual(store.last_source_archive_summary["count"], 1)
            self.assertEqual(archive.read_all()[0]["context"]["ingest_method"], "market_csv")
            self.assertEqual(archive.read_all()[0]["context"]["publish_posture"], "provider_review")

    def test_source_archive_writes_append_only_records(self) -> None:
        with TemporaryDirectory() as temp_dir:
            archive = SourceArchive(Path(temp_dir) / "source_archive.jsonl")
            item = SourceItem(
                id="source-1",
                source_type="fed_release",
                source_name="Federal Reserve",
                retrieved_at="2026-06-27T12:00:00Z",
                published_at="2026-06-27T12:00:00Z",
                canonical_url="https://example.com/fed",
                title="Fed sample release",
                summary="Official release sample.",
                primary_source=True,
                license_notes="Official source.",
                provenance={"feed_url": "https://example.com/feed"},
            )

            summary = archive.append_many([item], context={"feed_id": "fed_all_press"})
            records = archive.read_all()

            self.assertEqual(summary["count"], 1)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["source_id"], "source-1")
            self.assertEqual(records[0]["context"]["feed_id"], "fed_all_press")
            self.assertEqual(records[0]["source_item"]["provenance"]["feed_url"], "https://example.com/feed")

    def test_store_archives_ingested_rss_items(self) -> None:
        with TemporaryDirectory() as temp_dir:
            archive = SourceArchive(Path(temp_dir) / "source_archive.jsonl")
            ledger = DecisionLedger(Path(temp_dir) / "decisions.jsonl")
            item = SourceItem(
                id="rss-test-item",
                source_type="fed_release",
                source_name="Federal Reserve",
                retrieved_at="2026-06-27T12:00:00Z",
                published_at="2026-06-27T12:00:00Z",
                canonical_url="https://example.com/rss-item",
                title="Fed sample policy update",
                summary="Official release sample.",
                primary_source=True,
                license_notes="Official source.",
                provenance={"feed_url": "https://example.com/feed"},
            )
            store = EditorialStore(
                Path(__file__).parents[1] / "app" / "data" / "sample_sources.json",
                decision_ledger=ledger,
                source_archive=archive,
            )

            with patch("app.ingest.rss.fetch_rss_feed", return_value=[item]):
                result = store.ingest_rss("https://example.com/feed", "Federal Reserve", "fed_release")

            self.assertEqual(len(result), 1)
            self.assertEqual(store.last_source_archive_summary["count"], 1)
            self.assertEqual(store.source_archive_summary()["record_count"], 1)
            self.assertEqual(archive.read_all()[0]["context"]["ingest_method"], "rss")

    def test_export_story_slate_writes_editor_files(self) -> None:
        store = EditorialStore(Path(__file__).parents[1] / "app" / "data" / "sample_sources.json")

        with TemporaryDirectory() as temp_dir:
            result = export_story_slate(store.stories, Path(temp_dir), limit=2)

            self.assertTrue(Path(result["slate"]).exists())
            self.assertTrue(Path(result["newsletter"]["newsletter_json"]).exists())
            self.assertTrue(Path(result["newsletter"]["newsletter_markdown"]).exists())
            self.assertEqual(len(result["packages"]), 2)
            for package_files in result["packages"]:
                self.assertTrue(Path(package_files["story"]).exists())
                self.assertTrue(Path(package_files["package"]).exists())
                self.assertTrue(Path(package_files["qa"]).exists())
                self.assertTrue(Path(package_files["claims"]).exists())
                self.assertTrue(Path(package_files["rights"]).exists())
                self.assertTrue(Path(package_files["platform"]).exists())
                self.assertTrue(Path(package_files["approval"]).exists())
                self.assertTrue(Path(package_files["manifest"]).exists())
                self.assertTrue(Path(package_files["chart"]).exists())
                self.assertTrue(Path(package_files["storyboard"]).exists())
                self.assertTrue(Path(package_files["captions"]).exists())
                self.assertTrue(Path(package_files["preview"]).exists())
                self.assertTrue(Path(package_files["decision_template"]).exists())
                self.assertIn("editor_brief.md", package_files["brief"])

    def test_daily_brief_exports_owned_audience_summary(self) -> None:
        store = EditorialStore(Path(__file__).parents[1] / "app" / "data" / "sample_sources.json")

        brief = build_daily_brief(store.stories, limit=2)
        markdown = render_daily_brief_markdown(brief)

        self.assertEqual(brief["count"], 2)
        self.assertIn("Market Signal Daily Brief", markdown)
        self.assertIn("Not personalized investment advice", markdown)
        self.assertTrue(all(item["source_refs"] for item in brief["items"]))

    def test_daily_brief_export_writes_json_and_markdown(self) -> None:
        store = EditorialStore(Path(__file__).parents[1] / "app" / "data" / "sample_sources.json")

        with TemporaryDirectory() as temp_dir:
            result = export_daily_brief(store.stories, Path(temp_dir), limit=1)

            self.assertTrue(Path(result["newsletter_json"]).exists())
            self.assertTrue(Path(result["newsletter_markdown"]).exists())
            self.assertIn("daily_brief.md", result["newsletter_markdown"])

    def test_signal_chart_svg_contains_story_context(self) -> None:
        store = EditorialStore(Path(__file__).parents[1] / "app" / "data" / "sample_sources.json")
        story = store.stories[0]

        svg = render_signal_chart_svg(story)

        self.assertIn("<svg", svg)
        self.assertIn(story.primary_entity["ticker"], svg)
        self.assertIn("Not investment advice", svg)

    def test_claim_checklist_tracks_material_claims(self) -> None:
        store = EditorialStore(Path(__file__).parents[1] / "app" / "data" / "sample_sources.json")
        story = store.stories[0]
        package = generate_video_package(story)

        checklist = build_claim_checklist(story, package)

        self.assertEqual(checklist["story_id"], story.story_id)
        self.assertGreaterEqual(len(checklist["claims"]), 5)
        self.assertIn(checklist["status"], {"ready", "needs_review", "blocked"})
        self.assertTrue(any(claim["claim_id"] == "market_reaction" for claim in checklist["claims"]))

    def test_rights_report_flags_provider_review(self) -> None:
        store = EditorialStore(Path(__file__).parents[1] / "app" / "data" / "sample_sources.json")
        story = store.stories[0]

        report = build_rights_report(story)

        self.assertEqual(report["story_id"], story.story_id)
        self.assertIn(report["status"], {"ready", "needs_review", "blocked"})
        self.assertTrue(any(source["posture"] == "provider_review" for source in report["sources"]))
        self.assertTrue(report["required_actions"])

    def test_platform_readiness_tracks_originality_risk(self) -> None:
        store = EditorialStore(Path(__file__).parents[1] / "app" / "data" / "sample_sources.json")
        story = store.stories[0]
        package = generate_video_package(story)

        report = build_platform_readiness(story, package)

        self.assertEqual(report["story_id"], story.story_id)
        self.assertIn(report["status"], {"ready", "needs_review", "blocked"})
        self.assertGreater(report["originality_score"], 0.7)
        self.assertTrue(any(check["id"] == "source_reuse" for check in report["checks"]))
        self.assertTrue(report["required_actions"])

    def test_platform_readiness_blocks_generic_headline_recap(self) -> None:
        store = EditorialStore(Path(__file__).parents[1] / "app" / "data" / "sample_sources.json")
        story = store.stories[0]
        package = replace(
            generate_video_package(story),
            hook="Here are today's market headlines.",
            caption="Quick recap of today's stock news.",
            script_60s="Here are the headlines. This is a quick recap of today's market news.",
        )

        report = build_platform_readiness(story, package)

        self.assertEqual(report["status"], "blocked")
        self.assertTrue(any(check["id"] == "source_reuse" and check["status"] == "block" for check in report["checks"]))

    def test_approval_checklist_requires_notes_for_warnings(self) -> None:
        store = EditorialStore(Path(__file__).parents[1] / "app" / "data" / "sample_sources.json")
        story = store.stories[0]
        package = generate_video_package(story)

        approval = build_approval_checklist(story, package)

        self.assertEqual(approval["status"], "needs_review")
        self.assertTrue(approval["can_approve"])
        self.assertTrue(approval["notes_required"])
        self.assertTrue(any(check["id"] == "editor_accountability" for check in approval["checks"]))

    def test_store_rejects_approval_without_required_notes(self) -> None:
        with TemporaryDirectory() as temp_dir:
            store = EditorialStore(
                Path(__file__).parents[1] / "app" / "data" / "sample_sources.json",
                decision_ledger=DecisionLedger(Path(temp_dir) / "decisions.jsonl"),
            )
            story_id = store.stories[0].story_id

            with self.assertRaises(ValueError):
                store.record_decision(story_id, "approve", "editor", "")

            saved = store.record_decision(story_id, "approve", "editor", "Reviewed rights and claim warnings.")

            self.assertEqual(saved["decision"], "approve")
            self.assertEqual(saved["notes"], "Reviewed rights and claim warnings.")

    def test_publish_packet_blocks_until_editor_approval(self) -> None:
        with TemporaryDirectory() as temp_dir:
            store = EditorialStore(
                Path(__file__).parents[1] / "app" / "data" / "sample_sources.json",
                decision_ledger=DecisionLedger(Path(temp_dir) / "decisions.jsonl"),
            )
            story_id = store.stories[0].story_id

            packet = store.get_publish_packet(story_id)

            self.assertEqual(packet["status"], "blocked")
            self.assertFalse(packet["auto_post_allowed"])
            self.assertIn("Editor decision must be approve", packet["blockers"][0])

    def test_publish_packet_is_ready_after_approved_decision(self) -> None:
        with TemporaryDirectory() as temp_dir:
            store = EditorialStore(
                Path(__file__).parents[1] / "app" / "data" / "sample_sources.json",
                decision_ledger=DecisionLedger(Path(temp_dir) / "decisions.jsonl"),
            )
            story_id = store.stories[0].story_id

            store.record_decision(story_id, "approve", "editor", "Reviewed rights, claims, and platform warnings.")
            packet = store.get_publish_packet(story_id)

            self.assertEqual(packet["status"], "ready_manual_publish")
            self.assertEqual(packet["publish_mode"], "manual_only")
            self.assertFalse(packet["auto_post_allowed"])
            self.assertTrue(packet["warnings"])
            self.assertTrue(packet["source_citations"])

    def test_export_publish_packet_writes_manual_publish_files(self) -> None:
        with TemporaryDirectory() as temp_dir:
            store = EditorialStore(
                Path(__file__).parents[1] / "app" / "data" / "sample_sources.json",
                decision_ledger=DecisionLedger(Path(temp_dir) / "decisions.jsonl"),
            )
            story = store.stories[0]
            decision = store.record_decision(
                story.story_id,
                "approve",
                "editor",
                "Reviewed rights, claims, and platform warnings.",
            )

            files = export_publish_packet(story, decision, Path(temp_dir) / "publish")

            self.assertTrue(Path(files["publish_packet"]).exists())
            self.assertTrue(Path(files["publish_brief"]).exists())
            self.assertIn("manual_only", Path(files["publish_packet"]).read_text(encoding="utf-8"))
            self.assertIn("Auto-post allowed: False", Path(files["publish_brief"]).read_text(encoding="utf-8"))

    def test_storyboard_and_srt_are_render_ready(self) -> None:
        store = EditorialStore(Path(__file__).parents[1] / "app" / "data" / "sample_sources.json")
        story = store.stories[0]
        package = generate_video_package(story)

        storyboard = build_storyboard(story, package)
        srt = generate_srt(package)

        self.assertEqual(storyboard["format"], "vertical_1080x1920_60s")
        self.assertEqual(storyboard["editorial_format"]["key"], package.format_key)
        self.assertEqual(storyboard["duration_sec"], 60)
        self.assertEqual(len(storyboard["scenes"]), 6)
        self.assertIn("00:00:00,000 -->", srt)
        self.assertIn(package.hook, srt)

    def test_preview_html_contains_review_surfaces(self) -> None:
        store = EditorialStore(Path(__file__).parents[1] / "app" / "data" / "sample_sources.json")
        story = store.stories[0]
        package = generate_video_package(story)
        qa = run_qa(story, package)
        storyboard = build_storyboard(story, package)

        html = render_preview_html(story, package, storyboard, qa)

        self.assertIn("<!doctype html>", html)
        self.assertIn("Vertical video preview", html)
        self.assertIn("Source Trail", html)
        self.assertIn("QA Gates", html)

    def test_store_records_editorial_decision_with_qa_context(self) -> None:
        with TemporaryDirectory() as temp_dir:
            ledger = DecisionLedger(Path(temp_dir) / "decisions.jsonl")
            store = EditorialStore(
                Path(__file__).parents[1] / "app" / "data" / "sample_sources.json",
                decision_ledger=ledger,
            )
            story_id = store.stories[0].story_id

            pending = store.get_decision(story_id)
            saved = store.record_decision(story_id, "revise", "editor", "Tighten source caveat.")

            self.assertEqual(pending["decision"], "pending")
            self.assertEqual(saved["decision"], "revise")
            self.assertEqual(saved["notes"], "Tighten source caveat.")
            self.assertIn(saved["qa_status"], {"ready", "needs_review", "blocked"})
            self.assertGreater(saved["story_score"], 0)

    def test_editorial_decision_survives_store_restart(self) -> None:
        with TemporaryDirectory() as temp_dir:
            sample_path = Path(__file__).parents[1] / "app" / "data" / "sample_sources.json"
            ledger_path = Path(temp_dir) / "decisions.jsonl"
            first_store = EditorialStore(sample_path, decision_ledger=DecisionLedger(ledger_path))
            story_id = first_store.stories[0].story_id

            first_store.record_decision(story_id, "approve", "editor", "Looks ready.")
            restarted_store = EditorialStore(sample_path, decision_ledger=DecisionLedger(ledger_path))

            self.assertEqual(restarted_store.get_decision(story_id)["decision"], "approve")
            self.assertEqual(restarted_store.get_decision(story_id)["notes"], "Looks ready.")

    def test_editorial_override_survives_store_restart(self) -> None:
        with TemporaryDirectory() as temp_dir:
            sample_path = Path(__file__).parents[1] / "app" / "data" / "sample_sources.json"
            override_path = Path(temp_dir) / "overrides.jsonl"
            first_store = EditorialStore(
                sample_path,
                override_ledger=OverrideLedger(override_path),
            )
            story_id = first_store.stories[0].story_id

            saved = first_store.record_override(
                story_id,
                "primary_source",
                "editor",
                "Editor reviewed alternate evidence because official source is unavailable.",
                "internal://editorial/source-review/sample",
            )
            restarted_store = EditorialStore(
                sample_path,
                override_ledger=OverrideLedger(override_path),
            )

            self.assertEqual(saved["override_type"], "primary_source")
            self.assertEqual(len(restarted_store.get_overrides(story_id)), 1)
            self.assertEqual(restarted_store.get_overrides(story_id)[0]["reason"], saved["reason"])

    def test_source_terms_review_survives_store_restart(self) -> None:
        with TemporaryDirectory() as temp_dir:
            sample_path = Path(__file__).parents[1] / "app" / "data" / "sample_sources.json"
            terms_path = Path(temp_dir) / "source_terms.jsonl"
            first_store = EditorialStore(
                sample_path,
                source_terms_ledger=SourceTermsLedger(terms_path),
            )

            saved = first_store.record_source_terms(
                "Market data sample",
                "market_data",
                "internal_only",
                "internal://terms/market-data-sample",
                "editor",
                "Use for internal signal detection only.",
                "Do not show raw values in published outputs.",
            )
            restarted_store = EditorialStore(
                sample_path,
                source_terms_ledger=SourceTermsLedger(terms_path),
            )

            self.assertEqual(saved["review_status"], "internal_only")
            self.assertEqual(len(restarted_store.list_source_terms()), 1)
            self.assertEqual(restarted_store.list_source_terms()[0]["source_name"], "Market data sample")

def _sample_sec_submissions_payload() -> dict[str, object]:
    return {
        "cik": "0000320193",
        "name": "Apple Inc.",
        "tickers": ["AAPL"],
        "filings": {
            "recent": {
                "accessionNumber": ["0000320193-26-000001", "0000320193-26-000002"],
                "filingDate": ["2026-06-27", "2026-05-01"],
                "form": ["10-Q", "8-K"],
                "primaryDocument": ["aapl-20260627.htm", "aapl-20260501.htm"],
                "reportDate": ["2026-06-20", "2026-04-30"],
            }
        },
    }


def _sample_fred_observations_payload() -> dict[str, object]:
    return {
        "observations": [
            {
                "realtime_start": "2026-06-27",
                "realtime_end": "2026-06-27",
                "date": "2026-05-01",
                "value": "318.100",
            },
            {
                "realtime_start": "2026-06-27",
                "realtime_end": "2026-06-27",
                "date": "2026-04-01",
                "value": "317.200",
            },
            {
                "realtime_start": "2026-06-27",
                "realtime_end": "2026-06-27",
                "date": "2026-03-01",
                "value": ".",
            },
        ]
    }


def _sample_bls_timeseries_payload() -> dict[str, object]:
    return {
        "status": "REQUEST_SUCCEEDED",
        "message": [],
        "Results": {
            "series": [
                {
                    "seriesID": "CUUR0000SA0",
                    "data": [
                        {
                            "year": "2026",
                            "period": "M05",
                            "periodName": "May",
                            "value": "318.100",
                            "footnotes": [{}],
                        },
                        {
                            "year": "2026",
                            "period": "M04",
                            "periodName": "April",
                            "value": "317.200",
                            "footnotes": [{}],
                        },
                    ],
                }
            ]
        },
    }


def _sample_gdelt_payload() -> dict[str, object]:
    return {
        "articles": [
            {
                "title": "Nvidia shares move as investors weigh export control reports",
                "url": "https://example.com/news/nvidia-export-controls",
                "domain": "example.com",
                "sourceCommonName": "Example Markets",
                "language": "English",
                "seendate": "20260627123000",
                "sourceCountry": "US",
                "sourceCollection": "WEB",
            }
        ]
    }


if __name__ == "__main__":
    unittest.main()
