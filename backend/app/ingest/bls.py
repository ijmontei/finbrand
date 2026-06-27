from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any
from urllib.request import Request, urlopen

from app.models import SourceItem
from app.pipeline.entity_mapping import normalize_source_item


BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
BLS_LICENSE_NOTES = "Official BLS API data. Cite the series/release and avoid implying BLS endorsement."


def fetch_bls_timeseries(
    series_id: str,
    start_year: int,
    end_year: int,
    limit: int = 3,
    api_key: str | None = None,
) -> list[SourceItem]:
    payload = {
        "seriesid": [series_id],
        "startyear": str(start_year),
        "endyear": str(end_year),
    }
    key = api_key or os.getenv("BLS_API_KEY", "")
    if key.strip():
        payload["registrationkey"] = key.strip()
    response = _post_json(BLS_API_URL, payload)
    return bls_timeseries_payload_to_source_items(response, limit=limit)


def bls_timeseries_payload_to_source_items(payload: dict[str, Any], limit: int = 3) -> list[SourceItem]:
    series = payload.get("Results", {}).get("series", [])
    now = datetime.now(timezone.utc).isoformat()
    items: list[SourceItem] = []
    for series_payload in series:
        series_id = str(series_payload.get("seriesID", "")).strip().upper()
        observations = _sorted_observations(series_payload.get("data", []))[:limit]
        for observation in observations:
            year = str(observation.get("year", "")).strip()
            period = str(observation.get("period", "")).strip()
            period_name = str(observation.get("periodName", period)).strip()
            value = _float_value(observation.get("value"))
            date_label = f"{year}-{period}"
            item = SourceItem(
                id=_item_id(series_id, date_label, str(observation.get("value", ""))),
                source_type="bls_release",
                source_name="BLS API",
                retrieved_at=now,
                published_at=_published_at(year, period),
                canonical_url=f"https://data.bls.gov/timeseries/{series_id}",
                title=f"BLS {series_id} observation for {period_name} {year}",
                summary=f"Official BLS observation for {series_id}: {observation.get('value')} in {period_name} {year}.",
                themes=_themes_for_series(series_id),
                event_key=f"bls:{series_id}:{date_label}",
                primary_source=True,
                license_notes=BLS_LICENSE_NOTES,
                market={
                    "price_change_pct": 0.0,
                    "volume_vs_20d": 1.0,
                    "mention_velocity": 0.0,
                    "novelty_score": 0.74,
                    "series_value": value,
                },
                provenance={
                    "endpoint": BLS_API_URL,
                    "series_id": series_id,
                    "observation": observation,
                    "status": payload.get("status"),
                    "message": payload.get("message", []),
                },
            )
            items.append(normalize_source_item(item))
    return items


def _post_json(url: str, payload: dict[str, object]) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _sorted_observations(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(observations, key=lambda item: (str(item.get("year", "")), str(item.get("period", ""))), reverse=True)


def _themes_for_series(series_id: str) -> list[str]:
    upper = series_id.upper()
    if upper.startswith(("CU", "CW")):
        return ["inflation", "rates"]
    if upper.startswith(("LN", "CE", "LA", "JL")):
        return ["labor", "rates"]
    return ["macro"]


def _published_at(year: str, period: str) -> str:
    month = _period_month(period)
    if year.isdigit() and month:
        return f"{year}-{month:02}-01T00:00:00+00:00"
    return datetime.now(timezone.utc).isoformat()


def _period_month(period: str) -> int | None:
    clean = period.upper()
    if len(clean) == 3 and clean.startswith("M") and clean[1:].isdigit():
        month = int(clean[1:])
        if 1 <= month <= 12:
            return month
    return None


def _float_value(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _item_id(series_id: str, date_label: str, value: str) -> str:
    digest = hashlib.sha1(f"{series_id}:{date_label}:{value}".encode("utf-8")).hexdigest()[:12]
    return f"bls_{digest}"
