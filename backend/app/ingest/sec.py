from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any
from urllib.request import Request, urlopen

from app.models import SourceItem
from app.pipeline.entity_mapping import normalize_source_item


SEC_DATA_BASE = "https://data.sec.gov"
SEC_ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data"
SEC_LICENSE_NOTES = "Official SEC EDGAR data. Use a declared User-Agent, cite the filing, and respect SEC fair-access guidance."


def fetch_sec_submissions(cik: str, limit: int = 10, user_agent: str | None = None) -> list[SourceItem]:
    clean_cik = _clean_cik(cik)
    payload = _fetch_json(f"{SEC_DATA_BASE}/submissions/CIK{clean_cik}.json", user_agent)
    return submissions_payload_to_source_items(payload, limit=limit)


def submissions_payload_to_source_items(payload: dict[str, Any], limit: int = 10) -> list[SourceItem]:
    now = datetime.now(timezone.utc).isoformat()
    cik = _clean_cik(str(payload.get("cik", "")))
    entity_name = str(payload.get("name", "SEC filer")).strip() or "SEC filer"
    tickers = [str(ticker).upper() for ticker in payload.get("tickers", []) if str(ticker).strip()]
    recent = payload.get("filings", {}).get("recent", {})
    rows = _recent_rows(recent)[:limit]
    items = []
    for row in rows:
        form = str(row.get("form", "")).strip()
        accession = str(row.get("accessionNumber", "")).strip()
        filing_date = str(row.get("filingDate", "")).strip()
        report_date = str(row.get("reportDate", "")).strip()
        primary_document = str(row.get("primaryDocument", "")).strip()
        title = _title(entity_name, form, filing_date)
        item = SourceItem(
            id=_item_id(cik, accession, form, filing_date),
            source_type="sec_filing",
            source_name="SEC EDGAR submissions",
            retrieved_at=now,
            published_at=_published_at(filing_date),
            canonical_url=_filing_url(cik, accession, primary_document),
            title=title,
            summary=_summary(entity_name, form, filing_date, report_date),
            tickers=tickers,
            ciks=[cik],
            themes=["filings"],
            event_key=f"sec:{cik}:{accession or filing_date}",
            primary_source=True,
            license_notes=SEC_LICENSE_NOTES,
            provenance={
                "endpoint": f"{SEC_DATA_BASE}/submissions/CIK{cik}.json",
                "accession_number": accession,
                "form": form,
                "filing_date": filing_date,
                "report_date": report_date,
                "primary_document": primary_document,
            },
        )
        items.append(normalize_source_item(item))
    return items


def require_sec_user_agent(user_agent: str | None = None) -> str:
    value = user_agent or os.getenv("SEC_USER_AGENT", "")
    if not value.strip():
        raise ValueError("SEC_USER_AGENT is required for SEC EDGAR API access")
    return value.strip()


def _fetch_json(url: str, user_agent: str | None) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": require_sec_user_agent(user_agent)})
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _recent_rows(recent: dict[str, list[Any]]) -> list[dict[str, Any]]:
    forms = recent.get("form", [])
    rows = []
    for index, form in enumerate(forms):
        rows.append(
            {
                "form": form,
                "accessionNumber": _at(recent, "accessionNumber", index),
                "filingDate": _at(recent, "filingDate", index),
                "reportDate": _at(recent, "reportDate", index),
                "primaryDocument": _at(recent, "primaryDocument", index),
            }
        )
    return rows


def _at(values: dict[str, list[Any]], key: str, index: int) -> Any:
    items = values.get(key, [])
    return items[index] if index < len(items) else ""


def _clean_cik(cik: str) -> str:
    digits = "".join(char for char in cik if char.isdigit())
    return digits.zfill(10)


def _filing_url(cik: str, accession: str, primary_document: str) -> str:
    if not accession or not primary_document:
        return f"{SEC_DATA_BASE}/submissions/CIK{cik}.json"
    cik_int = str(int(cik)) if cik.strip("0") else "0"
    accession_path = accession.replace("-", "")
    return f"{SEC_ARCHIVES_BASE}/{cik_int}/{accession_path}/{primary_document}"


def _published_at(filing_date: str) -> str:
    if not filing_date:
        return datetime.now(timezone.utc).isoformat()
    return f"{filing_date}T00:00:00+00:00"


def _title(entity_name: str, form: str, filing_date: str) -> str:
    date = f" on {filing_date}" if filing_date else ""
    return f"{entity_name} filed {form}{date}".strip()


def _summary(entity_name: str, form: str, filing_date: str, report_date: str) -> str:
    report = f" for report period {report_date}" if report_date else ""
    date = f" on {filing_date}" if filing_date else ""
    return f"Official SEC submissions record: {entity_name} filed {form}{date}{report}."


def _item_id(cik: str, accession: str, form: str, filing_date: str) -> str:
    digest = hashlib.sha1(f"{cik}:{accession}:{form}:{filing_date}".encode("utf-8")).hexdigest()[:12]
    return f"sec_{digest}"
