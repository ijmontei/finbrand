from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser

from app.models import SourceItem
from app.pipeline.entity_mapping import normalize_source_item


def fetch_rss_feed(
    feed_url: str,
    source_name: str,
    source_type: str = "news_discovery",
    license_notes: str | None = None,
    user_agent: str | None = None,
) -> list[SourceItem]:
    request_headers = {
        "User-Agent": user_agent or os.getenv("SEC_USER_AGENT") or "Market Signal Studio research bot"
    }
    parsed = feedparser.parse(feed_url, request_headers=request_headers)
    now = datetime.now(timezone.utc).isoformat()
    items: list[SourceItem] = []
    for entry in parsed.entries[:30]:
        title = getattr(entry, "title", "").strip()
        link = getattr(entry, "link", feed_url)
        summary = getattr(entry, "summary", "")
        published = _published_at(entry)
        item_id = _item_id(source_name, link, title)
        item = SourceItem(
            id=item_id,
            source_type=source_type,
            source_name=source_name,
            retrieved_at=now,
            published_at=published,
            canonical_url=link,
            title=title,
            summary=summary,
            license_notes=license_notes
            or "RSS item for discovery or first-party summary; verify reuse rights before publication.",
            provenance={
                "feed_url": feed_url,
                "bozo": bool(getattr(parsed, "bozo", False)),
                "entry_snapshot": _entry_snapshot(entry),
            },
        )
        items.append(normalize_source_item(item))
    return items


def _published_at(entry: object) -> str:
    candidate = getattr(entry, "published", None) or getattr(entry, "updated", None)
    if not candidate:
        return datetime.now(timezone.utc).isoformat()
    try:
        return parsedate_to_datetime(candidate).astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        return datetime.now(timezone.utc).isoformat()


def _item_id(source_name: str, link: str, title: str) -> str:
    digest = hashlib.sha1(f"{source_name}:{link}:{title}".encode("utf-8")).hexdigest()[:12]
    return f"rss_{digest}"


def _entry_snapshot(entry: object) -> dict[str, object]:
    snapshot: dict[str, object] = {}
    for key in ["id", "title", "link", "published", "updated", "summary"]:
        value = getattr(entry, key, None)
        if value:
            snapshot[key] = str(value)
    tags = getattr(entry, "tags", None)
    if tags:
        snapshot["tags"] = [str(getattr(tag, "term", tag)) for tag in tags[:8]]
    return snapshot
