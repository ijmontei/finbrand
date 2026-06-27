from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

from app.models import SourceItem
from app.pipeline.entity_mapping import normalize_source_item


FRED_BASE = "https://api.stlouisfed.org/fred"
FRED_LICENSE_NOTES = "Official FRED API data. Cite the series and verify whether any underlying third-party content has redistribution limits."


def fetch_fred_observations(
    series_id: str,
    limit: int = 3,
    api_key: str | None = None,
) -> list[SourceItem]:
    key = require_fred_api_key(api_key)
    params = {
        "series_id": series_id,
        "api_key": key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": str(limit),
    }
    payload = _fetch_json(f"{FRED_BASE}/series/observations?{urlencode(params)}")
    return fred_observations_payload_to_source_items(series_id, payload, limit=limit)


def fred_observations_payload_to_source_items(
    series_id: str,
    payload: dict[str, Any],
    limit: int = 3,
) -> list[SourceItem]:
    observations = [
        observation
        for observation in payload.get("observations", [])[:limit]
        if str(observation.get("value", ".")).strip() not in {"", "."}
    ]
    now = datetime.now(timezone.utc).isoformat()
    items = []
    for observation in observations:
        date = str(observation.get("date", "")).strip()
        value = _float_value(observation.get("value"))
        title = f"FRED {series_id} observation for {date}"
        item = SourceItem(
            id=_item_id(series_id, date, str(observation.get("value", ""))),
            source_type="fred_series",
            source_name="FRED",
            retrieved_at=now,
            published_at=_published_at(date),
            canonical_url=f"https://fred.stlouisfed.org/series/{series_id.upper()}",
            title=title,
            summary=f"Official FRED observation for {series_id.upper()} on {date}: {observation.get('value')}.",
            themes=_themes_for_series(series_id),
            event_key=f"fred:{series_id.upper()}:{date}",
            primary_source=True,
            license_notes=FRED_LICENSE_NOTES,
            market={
                "price_change_pct": 0.0,
                "volume_vs_20d": 1.0,
                "mention_velocity": 0.0,
                "novelty_score": 0.72,
                "series_value": value,
            },
            provenance={
                "endpoint": f"{FRED_BASE}/series/observations",
                "series_id": series_id.upper(),
                "observation": observation,
            },
        )
        items.append(normalize_source_item(item))
    return items


def require_fred_api_key(api_key: str | None = None) -> str:
    value = api_key or os.getenv("FRED_API_KEY", "")
    if not value.strip():
        raise ValueError("FRED_API_KEY is required for FRED API access")
    return value.strip()


def _fetch_json(url: str) -> dict[str, Any]:
    with urlopen(url, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _themes_for_series(series_id: str) -> list[str]:
    upper = series_id.upper()
    if any(token in upper for token in ["CPI", "PCE", "INFL"]):
        return ["inflation", "rates"]
    if any(token in upper for token in ["UNRATE", "PAYEMS", "JOLTS", "WAGE"]):
        return ["labor", "rates"]
    if any(token in upper for token in ["DGS", "FEDFUNDS", "SOFR", "TREASURY"]):
        return ["rates"]
    return ["macro"]


def _published_at(date: str) -> str:
    if not date:
        return datetime.now(timezone.utc).isoformat()
    return f"{date}T00:00:00+00:00"


def _float_value(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _item_id(series_id: str, date: str, value: str) -> str:
    digest = hashlib.sha1(f"{series_id}:{date}:{value}".encode("utf-8")).hexdigest()[:12]
    return f"fred_{digest}"
