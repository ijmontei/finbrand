from __future__ import annotations

import re
from dataclasses import replace

from app.models import SourceItem


WATCHLIST = {
    "AAPL": ["apple", "iphone"],
    "AMD": ["advanced micro devices", "radeon", "epyc"],
    "GOOGL": ["alphabet", "google"],
    "MSFT": ["microsoft", "azure"],
    "NVDA": ["nvidia", "blackwell", "cuda"],
    "SMH": ["semiconductor etf", "semiconductor sector"],
    "SOXX": ["ishares semiconductor", "semiconductor etf"],
    "SPY": ["s&p 500", "s and p 500", "sp500"],
    "TSM": ["taiwan semiconductor", "tsmc"],
    "QQQ": ["nasdaq 100", "nasdaq-100"],
}

THEME_KEYWORDS = {
    "ai-infrastructure": ["ai", "accelerator", "gpu", "datacenter", "data center", "semiconductor"],
    "rates": ["fed", "rate", "yield", "treasury", "fomc", "higher-for-longer"],
    "inflation": ["cpi", "pce", "inflation", "prices"],
    "labor": ["payroll", "unemployment", "jobs", "wage"],
    "earnings": ["earnings", "revenue", "margin", "guidance", "eps"],
    "filings": ["8-k", "10-q", "10-k", "filing", "sec"],
    "consumer": ["retail", "restaurant", "travel", "credit card", "consumer"],
    "crypto": ["bitcoin", "ethereum", "crypto", "etf flow"],
}

SOURCE_AUTHORITY_BY_TYPE = {
    "sec_filing": 0.98,
    "fed_release": 0.97,
    "bls_release": 0.97,
    "fred_series": 0.93,
    "issuer_release": 0.88,
    "market_data": 0.72,
    "news_discovery": 0.48,
    "social_proxy": 0.30,
}


def normalize_source_item(item: SourceItem) -> SourceItem:
    text = _searchable_text(item)
    tickers = _dedupe([*item.tickers, *_tickers_from_text(text)])
    themes = _dedupe([*item.themes, *_themes_from_text(text)])
    primary_source = item.primary_source or item.source_type in {
        "sec_filing",
        "fed_release",
        "bls_release",
        "fred_series",
        "issuer_release",
    }
    source_authority = max(
        item.source_authority,
        SOURCE_AUTHORITY_BY_TYPE.get(item.source_type, 0.5),
    )
    entities = item.entities or [
        {"type": "ticker", "name": ticker, "confidence": 0.84} for ticker in tickers
    ]
    return replace(
        item,
        tickers=tickers,
        themes=themes,
        entities=entities,
        primary_source=primary_source,
        source_authority=round(source_authority, 2),
    )


def _searchable_text(item: SourceItem) -> str:
    return " ".join([item.title, item.summary, item.body_text]).lower()


def _tickers_from_text(text: str) -> list[str]:
    found: list[str] = []
    upper_tokens = set(re.findall(r"\b[A-Z]{1,5}\b", text.upper()))
    for ticker, aliases in WATCHLIST.items():
        if ticker in upper_tokens or any(alias in text for alias in aliases):
            found.append(ticker)
    return found


def _themes_from_text(text: str) -> list[str]:
    found: list[str] = []
    for theme, keywords in THEME_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            found.append(theme)
    return found


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        clean = value.strip()
        if clean and clean not in seen:
            seen.add(clean)
            result.append(clean)
    return result

