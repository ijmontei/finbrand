from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

from app.models import SourceItem
from app.pipeline.entity_mapping import normalize_source_item


GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_LICENSE_NOTES = "GDELT discovery item. Use for candidate discovery only; verify facts with primary or first-party sources before publication."


def fetch_gdelt_articles(query: str, limit: int = 10, timespan: str = "24h") -> list[SourceItem]:
    params = {
        "query": query,
        "mode": "ArtList",
        "format": "json",
        "maxrecords": str(limit),
        "sort": "datedesc",
        "timespan": timespan,
    }
    payload = _fetch_json(f"{GDELT_DOC_URL}?{urlencode(params)}")
    return gdelt_payload_to_source_items(payload, query=query, limit=limit, timespan=timespan)


def gdelt_payload_to_source_items(
    payload: dict[str, Any],
    query: str,
    limit: int = 10,
    timespan: str = "24h",
) -> list[SourceItem]:
    now = datetime.now(timezone.utc).isoformat()
    articles = payload.get("articles", [])[:limit]
    items = []
    for article in articles:
        title = str(article.get("title", "")).strip()
        url = str(article.get("url", "")).strip()
        if not title or not url:
            continue
        seen_date = str(article.get("seendate", "")).strip()
        source_name = str(article.get("sourceCommonName") or article.get("domain") or "GDELT DOC").strip()
        item = SourceItem(
            id=_item_id(url, title, seen_date),
            source_type="news_discovery",
            source_name=f"GDELT DOC: {source_name}",
            retrieved_at=now,
            published_at=_published_at(seen_date),
            canonical_url=url,
            title=title,
            summary=_summary(article),
            primary_source=False,
            source_authority=0.48,
            license_notes=GDELT_LICENSE_NOTES,
            market={
                "price_change_pct": 0.0,
                "volume_vs_20d": 1.0,
                "mention_velocity": 1.0,
                "novelty_score": 0.64,
            },
            provenance={
                "endpoint": GDELT_DOC_URL,
                "query": query,
                "timespan": timespan,
                "article": _article_snapshot(article),
            },
        )
        items.append(normalize_source_item(item))
    return items


def _fetch_json(url: str) -> dict[str, Any]:
    with urlopen(url, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _summary(article: dict[str, Any]) -> str:
    domain = article.get("domain") or article.get("sourceCommonName") or "source"
    language = article.get("language") or "unknown language"
    return f"Discovery candidate from {domain} via GDELT DOC API; language: {language}."


def _article_snapshot(article: dict[str, Any]) -> dict[str, object]:
    keys = [
        "title",
        "url",
        "domain",
        "sourceCommonName",
        "language",
        "seendate",
        "sourceCountry",
        "sourceCollection",
    ]
    return {key: article[key] for key in keys if key in article}


def _published_at(seen_date: str) -> str:
    if len(seen_date) >= 14 and seen_date[:14].isdigit():
        return (
            f"{seen_date[0:4]}-{seen_date[4:6]}-{seen_date[6:8]}T"
            f"{seen_date[8:10]}:{seen_date[10:12]}:{seen_date[12:14]}+00:00"
        )
    try:
        return datetime.fromisoformat(seen_date.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
    except ValueError:
        return datetime.now(timezone.utc).isoformat()


def _item_id(url: str, title: str, seen_date: str) -> str:
    digest = hashlib.sha1(f"{url}:{title}:{seen_date}".encode("utf-8")).hexdigest()[:12]
    return f"gdelt_{digest}"
