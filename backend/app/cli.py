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
        _print_json(export_story_slate(store.stories, Path(args.output_dir), args.limit))
    elif args.command == "newsletter":
        _print_json(export_daily_brief(store.stories, Path(args.output_dir), args.limit))
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
    elif args.command == "archive-status":
        _print_json(store.source_archive_summary())


def _print_json(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
