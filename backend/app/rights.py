from __future__ import annotations

from app.models import StoryCandidate


OFFICIAL_SOURCE_TYPES = {"sec_filing", "fed_release", "bls_release", "fred_series"}
FIRST_PARTY_SOURCE_TYPES = {"issuer_release"}
PROVIDER_REVIEW_SOURCE_TYPES = {"market_data", "news_discovery", "social_proxy"}


def build_rights_report(story: StoryCandidate) -> dict[str, object]:
    sources = [_source_rights(item) for item in story.source_trail]
    actions = _required_actions(sources)
    return {
        "story_id": story.story_id,
        "status": _status(sources),
        "summary": {
            "source_count": len(sources),
            "official_or_first_party": sum(1 for item in sources if item["posture"] in {"official", "first_party"}),
            "provider_review": sum(1 for item in sources if item["posture"] == "provider_review"),
            "missing_license_notes": sum(1 for item in sources if item["posture"] == "missing_notes"),
        },
        "sources": sources,
        "required_actions": actions,
        "publish_rule": "Use sources for discovery and verification; publish original commentary, charts, and short citations only.",
    }


def _source_rights(item: dict[str, object]) -> dict[str, object]:
    source_type = str(item.get("source_type", ""))
    license_notes = str(item.get("license_notes", "") or "")
    primary_source = bool(item.get("primary_source", False))
    posture = _posture(source_type, primary_source, license_notes)
    return {
        "source_id": item.get("id"),
        "source_name": item.get("source_name"),
        "source_type": source_type,
        "title": item.get("title"),
        "url": item.get("url"),
        "primary_source": primary_source,
        "license_notes": license_notes,
        "posture": posture,
        "risk_level": _risk_level(posture),
        "allowed_use": _allowed_use(posture),
        "review_action": _review_action(posture),
    }


def _posture(source_type: str, primary_source: bool, license_notes: str) -> str:
    notes = license_notes.lower()
    if not license_notes:
        return "missing_notes"
    if "redistribution review" in notes or source_type in PROVIDER_REVIEW_SOURCE_TYPES:
        return "provider_review"
    if source_type in OFFICIAL_SOURCE_TYPES:
        return "official"
    if primary_source or source_type in FIRST_PARTY_SOURCE_TYPES:
        return "first_party"
    return "unknown"


def _risk_level(posture: str) -> str:
    return {
        "official": "low",
        "first_party": "medium",
        "provider_review": "high",
        "missing_notes": "high",
        "unknown": "medium",
    }.get(posture, "medium")


def _allowed_use(posture: str) -> str:
    return {
        "official": "Use as primary evidence with attribution and short citations.",
        "first_party": "Summarize and link; avoid implying endorsement or republishing full release text.",
        "provider_review": "Use for internal signal detection until provider terms allow publication or redistribution.",
        "missing_notes": "Hold publication until usage notes are added.",
        "unknown": "Use for research only until source terms are reviewed.",
    }.get(posture, "Use for research only until source terms are reviewed.")


def _review_action(posture: str) -> str:
    return {
        "official": "Confirm source URL and publication date.",
        "first_party": "Confirm issuer/first-party ownership and summarize in original language.",
        "provider_review": "Confirm commercial use and redistribution terms before showing raw values.",
        "missing_notes": "Add license notes and source terms before editorial approval.",
        "unknown": "Classify source rights before approval.",
    }.get(posture, "Classify source rights before approval.")


def _required_actions(sources: list[dict[str, object]]) -> list[str]:
    actions = []
    for source in sources:
        action = str(source["review_action"])
        if action not in actions:
            actions.append(action)
    if not actions:
        actions.append("Attach at least one source before publication.")
    return actions


def _status(sources: list[dict[str, object]]) -> str:
    if not sources:
        return "blocked"
    high_risk = {"provider_review", "missing_notes"}
    if any(source["posture"] in high_risk for source in sources):
        return "needs_review"
    if any(source["posture"] == "unknown" for source in sources):
        return "needs_review"
    return "ready"

