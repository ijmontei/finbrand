from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.models import SourceTermsReview


DEFAULT_SOURCE_TERMS_LEDGER_PATH = Path(__file__).parents[2] / ".runtime" / "source_terms.jsonl"
REVIEW_STATUSES = {"approved_publish", "internal_only", "prohibited", "needs_review"}


class SourceTermsLedger:
    def __init__(self, path: Path | None = None) -> None:
        env_path = os.getenv("MARKET_SIGNAL_SOURCE_TERMS")
        if path is not None:
            self.path = path
        elif env_path:
            self.path = Path(env_path)
        else:
            self.path = DEFAULT_SOURCE_TERMS_LEDGER_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load_latest(self) -> dict[str, SourceTermsReview]:
        reviews: dict[str, SourceTermsReview] = {}
        if not self.path.exists():
            return reviews
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                clean = line.strip()
                if not clean:
                    continue
                review = SourceTermsReview(**json.loads(clean))
                reviews[terms_key(review.source_type, review.source_name)] = review
        return reviews

    def append(self, review: SourceTermsReview) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(review.to_dict(), sort_keys=True) + "\n")


def terms_key(source_type: str, source_name: str) -> str:
    return f"{source_type.strip().lower()}::{source_name.strip().lower()}"


def find_terms_review(
    source: dict[str, object],
    reviews: dict[str, SourceTermsReview | dict[str, Any]],
) -> SourceTermsReview | dict[str, Any] | None:
    source_type = str(source.get("source_type", ""))
    source_name = str(source.get("source_name", ""))
    return reviews.get(terms_key(source_type, source_name)) or reviews.get(terms_key(source_type, "*"))


def serialize_terms_reviews(reviews: list[SourceTermsReview | dict[str, Any]] | dict[str, SourceTermsReview] | None) -> list[dict[str, object]]:
    if reviews is None:
        return []
    values = reviews.values() if isinstance(reviews, dict) else reviews
    result = []
    for review in values:
        if isinstance(review, SourceTermsReview):
            result.append(review.to_dict())
        else:
            result.append(dict(review))
    return result


def terms_reviews_by_key(reviews: list[SourceTermsReview | dict[str, Any]] | dict[str, SourceTermsReview] | None) -> dict[str, SourceTermsReview | dict[str, Any]]:
    return {
        terms_key(str(review["source_type"]), str(review["source_name"])): review
        for review in serialize_terms_reviews(reviews)
    }


def validate_terms_review(
    source_name: str,
    source_type: str,
    review_status: str,
    terms_url: str,
    reviewed_by: str,
    allowed_use: str,
    restrictions: str,
) -> None:
    if not source_name.strip():
        raise ValueError("source_name is required for source terms review")
    if not source_type.strip():
        raise ValueError("source_type is required for source terms review")
    if review_status not in REVIEW_STATUSES:
        raise ValueError(f"review_status must be one of: {', '.join(sorted(REVIEW_STATUSES))}")
    if not terms_url.strip().startswith(("http://", "https://", "internal://")):
        raise ValueError("terms_url must be an http(s) URL or internal:// reference")
    if not reviewed_by.strip():
        raise ValueError("reviewed_by is required for source terms review")
    if len(allowed_use.strip()) < 10:
        raise ValueError("allowed_use must describe the reviewed usage")
    if not restrictions.strip():
        raise ValueError("restrictions must describe limits, even if no extra restrictions were found")


def review_is_expired(review: SourceTermsReview | dict[str, Any] | None, now: datetime | None = None) -> bool:
    if not review:
        return False
    expires_at = _field(review, "expires_at", "")
    if not expires_at:
        return False
    now = now or datetime.now(timezone.utc)
    try:
        expires = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
    except ValueError:
        return True
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return expires <= now


def _field(review: SourceTermsReview | dict[str, Any], name: str, default: Any = None) -> Any:
    if isinstance(review, SourceTermsReview):
        return getattr(review, name, default)
    return review.get(name, default)
