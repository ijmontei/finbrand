from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.exporter import export_story_slate
from app.ingest.catalog import find_source_feed, load_source_catalog
from app.newsletter import export_daily_brief
from app.store import EditorialStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Market Signal Studio command line tools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("catalog", help="List configured official source feeds")

    slate_parser = subparsers.add_parser("slate", help="Print the ranked story slate as JSON")
    slate_parser.add_argument("--limit", type=int, default=5)

    package_parser = subparsers.add_parser("package", help="Generate one story package as JSON")
    package_parser.add_argument("story_id")

    qa_parser = subparsers.add_parser("qa", help="Run QA for one story")
    qa_parser.add_argument("story_id")

    export_parser = subparsers.add_parser("export", help="Export editor-ready files")
    export_parser.add_argument("--output-dir", default="exports/latest")
    export_parser.add_argument("--limit", type=int, default=5)

    newsletter_parser = subparsers.add_parser("newsletter", help="Export an owned-audience daily brief")
    newsletter_parser.add_argument("--output-dir", default="exports/newsletter")
    newsletter_parser.add_argument("--limit", type=int, default=3)

    ingest_parser = subparsers.add_parser("ingest-feed", help="Ingest one configured RSS feed")
    ingest_parser.add_argument("feed_id")

    sec_parser = subparsers.add_parser("sec-submissions", help="Ingest recent SEC submissions for one CIK")
    sec_parser.add_argument("cik")
    sec_parser.add_argument("--limit", type=int, default=10)

    fred_parser = subparsers.add_parser("fred-observations", help="Ingest recent FRED observations for one series")
    fred_parser.add_argument("series_id")
    fred_parser.add_argument("--limit", type=int, default=3)

    bls_parser = subparsers.add_parser("bls-timeseries", help="Ingest recent BLS time-series observations")
    bls_parser.add_argument("series_id")
    bls_parser.add_argument("--start-year", type=int, required=True)
    bls_parser.add_argument("--end-year", type=int, required=True)
    bls_parser.add_argument("--limit", type=int, default=3)

    gdelt_parser = subparsers.add_parser("gdelt-search", help="Ingest GDELT article discovery candidates")
    gdelt_parser.add_argument("query", nargs="+")
    gdelt_parser.add_argument("--limit", type=int, default=10)
    gdelt_parser.add_argument("--timespan", default="24h")

    market_parser = subparsers.add_parser("market-csv", help="Ingest rights-reviewed market data from a CSV file")
    market_parser.add_argument("path")
    market_parser.add_argument("--source-name", default=None)

    override_parser = subparsers.add_parser("override-primary-source", help="Record an audited primary-source override")
    override_parser.add_argument("story_id")
    override_parser.add_argument("--editor", default="editor")
    override_parser.add_argument("--reason", required=True)
    override_parser.add_argument("--evidence-url", required=True)

    subparsers.add_parser("archive-status", help="Show local raw source archive status")

    args = parser.parse_args()
    store = EditorialStore()

    if args.command == "catalog":
        _print_json([feed.to_dict() for feed in load_source_catalog()])
    elif args.command == "slate":
        _print_json([story.to_dict() for story in store.stories[: args.limit]])
    elif args.command == "package":
        _print_json(store.get_or_generate_package(args.story_id).to_dict())
    elif args.command == "qa":
        _print_json(store.get_qa(args.story_id))
    elif args.command == "export":
        _print_json(export_story_slate(store.stories, Path(args.output_dir), args.limit, store.overrides_by_story()))
    elif args.command == "newsletter":
        _print_json(export_daily_brief(store.stories, Path(args.output_dir), args.limit, store.overrides_by_story()))
    elif args.command == "ingest-feed":
        feed = find_source_feed(args.feed_id)
        result = store.ingest_rss(
            feed.feed_url,
            feed.source_name,
            feed.source_type,
            license_notes=feed.license_notes,
        )
        _print_json(
            {
                "feed": feed.to_dict(),
                "ingested": len(result),
                "archive": store.last_source_archive_summary,
                "stories": store.list_stories(),
            }
        )
    elif args.command == "sec-submissions":
        try:
            result = store.ingest_sec_submissions(args.cik, limit=args.limit)
        except ValueError as exc:
            _print_json(
                {
                    "error": str(exc),
                    "hint": "Set SEC_USER_AGENT to a real app/contact string before calling SEC EDGAR.",
                }
            )
            raise SystemExit(2) from exc
        _print_json(
            {
                "cik": args.cik,
                "ingested": len(result),
                "archive": store.last_source_archive_summary,
                "stories": store.list_stories(),
            }
        )
    elif args.command == "fred-observations":
        try:
            result = store.ingest_fred_observations(args.series_id, limit=args.limit)
        except ValueError as exc:
            _print_json(
                {
                    "error": str(exc),
                    "hint": "Set FRED_API_KEY before calling the FRED API.",
                }
            )
            raise SystemExit(2) from exc
        _print_json(
            {
                "series_id": args.series_id,
                "ingested": len(result),
                "archive": store.last_source_archive_summary,
                "stories": store.list_stories(),
            }
        )
    elif args.command == "bls-timeseries":
        result = store.ingest_bls_timeseries(
            args.series_id,
            start_year=args.start_year,
            end_year=args.end_year,
            limit=args.limit,
        )
        _print_json(
            {
                "series_id": args.series_id,
                "ingested": len(result),
                "archive": store.last_source_archive_summary,
                "stories": store.list_stories(),
            }
        )
    elif args.command == "gdelt-search":
        query = " ".join(args.query)
        result = store.ingest_gdelt_articles(query, limit=args.limit, timespan=args.timespan)
        _print_json(
            {
                "query": query,
                "ingested": len(result),
                "archive": store.last_source_archive_summary,
                "publish_posture": "discovery_only",
                "stories": store.list_stories(),
            }
        )
    elif args.command == "market-csv":
        result = store.ingest_market_csv(Path(args.path), source_name=args.source_name)
        _print_json(
            {
                "path": args.path,
                "ingested": len(result),
                "archive": store.last_source_archive_summary,
                "publish_posture": "provider_review",
                "stories": store.list_stories(),
            }
        )
    elif args.command == "override-primary-source":
        result = store.record_override(
            args.story_id,
            "primary_source",
            args.editor,
            args.reason,
            args.evidence_url,
        )
        _print_json(
            {
                "override": result,
                "qa": store.get_qa(args.story_id),
                "approval": store.get_approval(args.story_id),
            }
        )
    elif args.command == "archive-status":
        _print_json(store.source_archive_summary())


def _print_json(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
