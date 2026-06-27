from __future__ import annotations

import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from app.models import SourceItem
from app.pipeline.entity_mapping import normalize_source_item


DEFAULT_SOURCE_NAME = "Market data CSV"
DEFAULT_LICENSE_NOTES = "Imported market data. Provider redistribution review required before publication."


def load_market_csv(path: Path | str, source_name: str = DEFAULT_SOURCE_NAME) -> list[SourceItem]:
    csv_path = Path(path)
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("market CSV must include a header row")
        rows = list(reader)
    return market_csv_rows_to_source_items(rows, source_name=source_name, csv_path=csv_path)


def market_csv_rows_to_source_items(
    rows: list[dict[str, str]],
    source_name: str = DEFAULT_SOURCE_NAME,
    csv_path: Path | None = None,
) -> list[SourceItem]:
    now = datetime.now(timezone.utc).isoformat()
    items: list[SourceItem] = []
    for index, row in enumerate(rows, start=1):
        normalized_row = _normalize_row(row)
        ticker = normalized_row.get("ticker", "").upper()
        if not ticker:
            raise ValueError(f"market CSV row {index} is missing ticker")
        published_at = _published_at(normalized_row)
        row_source_name = normalized_row.get("source_name") or source_name
        item = SourceItem(
            id=_item_id(ticker, published_at, normalized_row, index),
            source_type="market_data",
            source_name=row_source_name,
            retrieved_at=now,
            published_at=published_at,
            canonical_url=_canonical_url(ticker, published_at, normalized_row),
            title=_title(ticker, normalized_row),
            summary=_summary(ticker, normalized_row),
            tickers=_tickers(ticker, normalized_row),
            themes=_split_list(normalized_row.get("themes", "")),
            event_key=normalized_row.get("event_key") or f"market:{ticker}:{published_at[:10]}",
            primary_source=False,
            source_authority=0.72,
            license_notes=normalized_row.get("license_notes") or DEFAULT_LICENSE_NOTES,
            market={
                "price_change_pct": _float_value(normalized_row.get("price_change_pct"), 0.0),
                "volume_vs_20d": _float_value(normalized_row.get("volume_vs_20d"), 1.0),
                "mention_velocity": _float_value(normalized_row.get("mention_velocity"), 0.0),
                "novelty_score": _float_value(normalized_row.get("novelty_score"), 0.68),
            },
            provenance={
                "provider": row_source_name,
                "csv_path": str(csv_path) if csv_path else "",
                "row_number": index,
                "row": normalized_row,
                "publish_posture": "provider_review",
            },
        )
        items.append(normalize_source_item(item))
    return items


def _normalize_row(row: dict[str, str]) -> dict[str, str]:
    return {str(key or "").strip().lower(): str(value or "").strip() for key, value in row.items()}


def _published_at(row: dict[str, str]) -> str:
    value = row.get("published_at") or row.get("datetime") or row.get("date")
    if not value:
        return datetime.now(timezone.utc).isoformat()
    clean = value.strip()
    if len(clean) == 10:
        try:
            datetime.fromisoformat(clean)
        except ValueError:
            return datetime.now(timezone.utc).isoformat()
        return f"{clean}T00:00:00+00:00"
    try:
        return datetime.fromisoformat(clean.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
    except ValueError:
        return datetime.now(timezone.utc).isoformat()


def _canonical_url(ticker: str, published_at: str, row: dict[str, str]) -> str:
    if row.get("canonical_url"):
        return str(row["canonical_url"])
    return f"provider://market-data/{ticker}/{published_at[:10]}"


def _title(ticker: str, row: dict[str, str]) -> str:
    if row.get("title"):
        return str(row["title"])
    change = _float_value(row.get("price_change_pct"), 0.0)
    direction = "up" if change >= 0 else "down"
    return f"{ticker} market reaction {direction} {abs(change):.2f}%"


def _summary(ticker: str, row: dict[str, str]) -> str:
    if row.get("summary"):
        return str(row["summary"])
    change = _float_value(row.get("price_change_pct"), 0.0)
    volume = _float_value(row.get("volume_vs_20d"), 1.0)
    return f"Imported market-data signal for {ticker}: {change:.2f}% move with {volume:.2f}x 20-day volume."


def _tickers(ticker: str, row: dict[str, str]) -> list[str]:
    values = [ticker]
    values.extend(_split_list(row.get("tickers", "")))
    if row.get("sector_etf"):
        values.append(str(row["sector_etf"]).upper())
    return _dedupe([value.upper() for value in values])


def _split_list(value: str) -> list[str]:
    clean = value.replace("|", ",").replace(";", ",")
    return [part.strip() for part in clean.split(",") if part.strip()]


def _float_value(value: object, default: float) -> float:
    try:
        if value is None or value == "":
            return default
        return float(str(value).replace("%", "").replace(",", ""))
    except (TypeError, ValueError):
        return default


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        clean = value.strip()
        if clean and clean not in seen:
            seen.add(clean)
            result.append(clean)
    return result


def _item_id(ticker: str, published_at: str, row: dict[str, str], index: int) -> str:
    seed = row.get("id") or f"{ticker}:{published_at}:{row.get('event_key', '')}:{index}"
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]
    return f"market_csv_{digest}"
