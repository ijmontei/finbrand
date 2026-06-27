from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import datetime, timezone
from statistics import mean

from app.models import SourceItem, StoryCandidate
from app.pipeline.entity_mapping import normalize_source_item


OFFICIAL_SOURCE_TYPES = {"sec_filing", "fed_release", "bls_release", "fred_series", "issuer_release"}


def build_story_candidates(items: list[SourceItem], now: datetime | None = None) -> list[StoryCandidate]:
    now = now or datetime.now(timezone.utc)
    normalized = [normalize_source_item(item) for item in items]
    groups: dict[str, list[SourceItem]] = defaultdict(list)
    for item in normalized:
        groups[_cluster_key(item)].append(item)

    stories = [_story_from_group(key, group, now) for key, group in groups.items()]
    return sorted(stories, key=lambda story: story.scores["story_score"], reverse=True)


def _story_from_group(key: str, group: list[SourceItem], now: datetime) -> StoryCandidate:
    primary = max(group, key=lambda item: (item.source_authority, item.market.get("price_change_pct", 0)))
    story_type = _classify_story_type(primary)
    metrics = _aggregate_metrics(group, now)
    scores = _score_story(group, metrics)
    primary_entity = _primary_entity(group)
    source_trail = [
        {
            "id": item.id,
            "source_name": item.source_name,
            "source_type": item.source_type,
            "title": item.title,
            "url": item.canonical_url,
            "primary_source": item.primary_source,
            "license_notes": item.license_notes,
        }
        for item in sorted(group, key=lambda value: value.source_authority, reverse=True)
    ]
    story_id = "story_" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]
    return StoryCandidate(
        story_id=story_id,
        story_date=primary.published_at[:10],
        headline=_headline(primary, story_type, primary_entity),
        story_type=story_type,
        primary_entity=primary_entity,
        supporting_entities=_supporting_entities(group, primary_entity),
        cluster_item_ids=[item.id for item in group],
        primary_evidence=_primary_evidence(group),
        metrics=metrics,
        scores=scores,
        angles=_angles_for(story_type),
        risk_flags=_risk_flags(group),
        editorial_state=_editorial_state(scores),
        source_trail=source_trail,
    )


def _cluster_key(item: SourceItem) -> str:
    if item.event_key:
        return item.event_key
    if item.tickers:
        return f"ticker:{item.tickers[0]}:{item.published_at[:10]}"
    if item.themes:
        return f"theme:{item.themes[0]}:{item.published_at[:10]}"
    words = "-".join(item.title.lower().split()[:8])
    return f"title:{words}:{item.published_at[:10]}"


def _classify_story_type(item: SourceItem) -> str:
    themes = set(item.themes)
    if item.source_type == "sec_filing" or "filings" in themes:
        return "single_stock_filing"
    if item.source_type in {"bls_release", "fred_series"} or {"inflation", "labor"} & themes:
        return "macro_release"
    if item.source_type == "fed_release" or "rates" in themes:
        return "fed_policy"
    if "earnings" in themes:
        return "earnings_followthrough"
    if item.tickers and ("ai-infrastructure" in themes or "consumer" in themes):
        return "single_stock_market_reaction"
    return "sector_movers"


def _aggregate_metrics(group: list[SourceItem], now: datetime) -> dict[str, float | int | bool]:
    price_moves = [float(item.market.get("price_change_pct", 0.0)) for item in group]
    volume = [float(item.market.get("volume_vs_20d", 1.0)) for item in group]
    mention_velocity = [float(item.market.get("mention_velocity", 0.0)) for item in group]
    published = [_parse_dt(item.published_at) for item in group]
    newest_hours = min(max((now - value).total_seconds() / 3600, 0.0) for value in published)
    return {
        "price_change_pct": round(max(price_moves, key=abs) if price_moves else 0.0, 2),
        "volume_vs_20d": round(max(volume) if volume else 1.0, 2),
        "mention_velocity": round(max(mention_velocity) if mention_velocity else 0.0, 2),
        "source_count": len(group),
        "primary_source_count": sum(1 for item in group if item.primary_source),
        "unique_source_count": len({item.source_name for item in group}),
        "hours_since_latest": round(newest_hours, 2),
        "has_chartable_metric": any(item.market for item in group),
        "has_primary_source": any(item.source_type in OFFICIAL_SOURCE_TYPES for item in group),
    }


def _score_story(group: list[SourceItem], metrics: dict[str, float | int | bool]) -> dict[str, float]:
    market_impact = min(
        1.0,
        (abs(float(metrics["price_change_pct"])) / 8.0 * 0.65)
        + ((float(metrics["volume_vs_20d"]) - 1.0) / 3.0 * 0.25)
        + (float(metrics["mention_velocity"]) / 100.0 * 0.10),
    )
    source_authority = mean(item.source_authority for item in group)
    novelty = max(float(item.market.get("novelty_score", 0.62)) for item in group)
    timeliness = max(0.1, 1.0 - (float(metrics["hours_since_latest"]) / 36.0))
    corroboration = min(1.0, float(metrics["unique_source_count"]) / 3.0)
    explainability = _explainability(group, metrics)
    buzz_proxy = min(1.0, float(metrics["mention_velocity"]) / 80.0)
    story_score = (
        0.30 * market_impact
        + 0.20 * novelty
        + 0.15 * source_authority
        + 0.10 * timeliness
        + 0.10 * corroboration
        + 0.10 * explainability
        + 0.05 * buzz_proxy
    )
    return {
        "market_impact": round(market_impact, 3),
        "novelty": round(novelty, 3),
        "source_authority": round(source_authority, 3),
        "timeliness": round(timeliness, 3),
        "corroboration": round(corroboration, 3),
        "explainability": round(explainability, 3),
        "buzz_proxy": round(buzz_proxy, 3),
        "story_score": round(story_score, 3),
    }


def _explainability(group: list[SourceItem], metrics: dict[str, float | int | bool]) -> float:
    points = 0.15
    if metrics["has_primary_source"]:
        points += 0.30
    if metrics["has_chartable_metric"]:
        points += 0.25
    if any(item.tickers or item.themes for item in group):
        points += 0.15
    if any(item.summary for item in group):
        points += 0.15
    return min(1.0, points)


def _primary_entity(group: list[SourceItem]) -> dict[str, str]:
    for item in group:
        if item.tickers:
            return {"ticker": item.tickers[0], "name": _entity_name(item.tickers[0])}
    themes = [theme for item in group for theme in item.themes]
    if themes:
        label = themes[0].replace("-", " ").title()
        return {"ticker": "MACRO", "name": label}
    return {"ticker": "MARKET", "name": "Market Story"}


def _entity_name(ticker: str) -> str:
    names = {
        "AAPL": "Apple",
        "AMD": "Advanced Micro Devices",
        "GOOGL": "Alphabet",
        "MSFT": "Microsoft",
        "NVDA": "Nvidia",
        "SMH": "VanEck Semiconductor ETF",
        "SOXX": "iShares Semiconductor ETF",
        "SPY": "S&P 500 ETF",
        "TSM": "Taiwan Semiconductor",
        "QQQ": "Nasdaq 100 ETF",
    }
    return names.get(ticker, ticker)


def _supporting_entities(group: list[SourceItem], primary_entity: dict[str, str]) -> list[str]:
    primary = primary_entity.get("ticker")
    values = []
    for item in group:
        values.extend(item.tickers)
        values.extend(theme.replace("-", " ") for theme in item.themes)
    deduped = []
    for value in values:
        if value != primary and value not in deduped:
            deduped.append(value)
    return deduped[:6]


def _primary_evidence(group: list[SourceItem]) -> list[dict[str, str]]:
    evidence = []
    for item in sorted(group, key=lambda value: value.source_authority, reverse=True):
        if item.primary_source or item.source_type in OFFICIAL_SOURCE_TYPES:
            evidence.append({"kind": item.source_type, "ref": item.id, "source_name": item.source_name})
    return evidence[:3]


def _headline(item: SourceItem, story_type: str, primary_entity: dict[str, str]) -> str:
    entity = primary_entity["name"]
    if story_type == "macro_release":
        return f"{entity} data is moving the market narrative"
    if story_type == "fed_policy":
        return "Rates story shifts on official Fed language"
    if story_type == "single_stock_filing":
        return f"{entity} filing gives the market a fresh data point"
    if story_type == "earnings_followthrough":
        return f"{entity} reaction turns on earnings quality"
    if story_type == "single_stock_market_reaction":
        return f"{entity} move looks bigger than a headline recap"
    return item.title


def _angles_for(story_type: str) -> list[str]:
    angles = {
        "macro_release": ["The number", "The rate reaction", "What must confirm next"],
        "fed_policy": ["The wording", "The yield reaction", "The close matters"],
        "single_stock_filing": ["The disclosed fact", "The market timestamp", "What the filing does not answer"],
        "earnings_followthrough": ["The headline beat", "The margin or guide", "The next-quarter test"],
        "single_stock_market_reaction": ["The story everyone saw", "The data everyone missed", "The caveat"],
        "sector_movers": ["The shared theme", "The crowded trade", "The reversal risk"],
    }
    return angles.get(story_type, angles["sector_movers"])


def _risk_flags(group: list[SourceItem]) -> list[str]:
    flags = ["not_personalized_advice", "avoid_price_target_language"]
    if not any(item.primary_source for item in group):
        flags.append("needs_primary_source_review")
    if any("redistribution" in item.license_notes.lower() for item in group):
        flags.append("market_data_rights_review")
    return flags


def _editorial_state(scores: dict[str, float]) -> str:
    if scores["story_score"] >= 0.80:
        return "draft_ready"
    if scores["story_score"] >= 0.65:
        return "editor_review"
    return "archive"


def _parse_dt(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)

