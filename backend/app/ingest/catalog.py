from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class SourceFeed:
    id: str
    source_name: str
    source_type: str
    feed_url: str
    license_notes: str

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "source_name": self.source_name,
            "source_type": self.source_type,
            "feed_url": self.feed_url,
            "license_notes": self.license_notes,
        }


def load_source_catalog(path: Path | None = None) -> list[SourceFeed]:
    catalog_path = path or Path(__file__).parents[1] / "data" / "source_feeds.json"
    with catalog_path.open("r", encoding="utf-8") as handle:
        raw_feeds = json.load(handle)
    return [SourceFeed(**feed) for feed in raw_feeds]


def find_source_feed(feed_id: str, path: Path | None = None) -> SourceFeed:
    for feed in load_source_catalog(path):
        if feed.id == feed_id:
            return feed
    raise KeyError(feed_id)

