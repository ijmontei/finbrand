from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.models import SourceItem


DEFAULT_SOURCE_ARCHIVE_PATH = Path(__file__).parents[2] / ".runtime" / "source_archive.jsonl"


class SourceArchive:
    def __init__(self, path: Path | None = None) -> None:
        env_path = os.getenv("MARKET_SIGNAL_SOURCE_ARCHIVE")
        if path is not None:
            self.path = path
        elif env_path:
            self.path = Path(env_path)
        else:
            self.path = DEFAULT_SOURCE_ARCHIVE_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append_many(self, items: list[SourceItem], context: dict[str, Any] | None = None) -> dict[str, object]:
        archived_at = datetime.now(timezone.utc).isoformat()
        records = [self._record(item, archived_at, context or {}) for item in items]
        if records:
            with self.path.open("a", encoding="utf-8") as handle:
                for record in records:
                    handle.write(json.dumps(record, sort_keys=True) + "\n")
        return {
            "path": str(self.path),
            "count": len(records),
            "archive_ids": [record["archive_id"] for record in records],
        }

    def summary(self) -> dict[str, object]:
        records = self.read_all()
        return {
            "path": str(self.path),
            "exists": self.path.exists(),
            "record_count": len(records),
            "latest_archived_at": records[-1]["archived_at"] if records else None,
        }

    def read_all(self) -> list[dict[str, object]]:
        if not self.path.exists():
            return []
        records = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                clean = line.strip()
                if clean:
                    records.append(json.loads(clean))
        return records

    def _record(self, item: SourceItem, archived_at: str, context: dict[str, Any]) -> dict[str, object]:
        source_item = item.to_dict()
        archive_id = _archive_id(item.id, archived_at, source_item.get("canonical_url", ""))
        return {
            "archive_id": archive_id,
            "archived_at": archived_at,
            "source_id": item.id,
            "source_name": item.source_name,
            "source_type": item.source_type,
            "canonical_url": item.canonical_url,
            "published_at": item.published_at,
            "retrieved_at": item.retrieved_at,
            "context": context,
            "source_item": source_item,
        }


def _archive_id(source_id: str, archived_at: str, canonical_url: str) -> str:
    digest = hashlib.sha1(f"{source_id}:{archived_at}:{canonical_url}".encode("utf-8")).hexdigest()[:14]
    return f"archive_{digest}"
