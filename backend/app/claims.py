from __future__ import annotations

from app.models import StoryCandidate, VideoPackage
from app.overrides import has_override, override_refs, serialize_overrides


def build_claim_checklist(
    story: StoryCandidate,
    package: VideoPackage,
    editorial_overrides: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    overrides = serialize_overrides(editorial_overrides)
    source_refs = [item["id"] for item in story.source_trail]
    primary_refs = [item["ref"] for item in story.primary_evidence]
    primary_override_refs = override_refs(overrides, "primary_source")
    claims = [
        _claim(
            "primary_evidence",
            f"The story has primary or first-party evidence attached: {_source_names(story)}.",
            primary_refs or primary_override_refs,
            _primary_evidence_status(primary_refs, overrides),
            _primary_evidence_note(primary_refs, overrides),
        ),
        _claim(
            "market_reaction",
            f"The visible market reaction is {story.metrics.get('price_change_pct', 0)}% with volume near {story.metrics.get('volume_vs_20d', 1)} times normal.",
            source_refs,
            "editor_verify",
            "Verify market-data provider terms and final numeric values before rendering.",
        ),
        _claim(
            "story_classification",
            f"This package frames the event as {story.story_type.replace('_', ' ')}.",
            source_refs,
            "editor_verify",
            "Confirm the framing does not overstate causality.",
        ),
        _claim(
            "why_it_matters",
            package.why_it_matters,
            source_refs,
            "editor_verify",
            "Keep this as analysis, not a personalized recommendation.",
        ),
        _claim(
            "chart",
            package.chart_idea,
            source_refs,
            "editor_verify",
            "Confirm the chart uses licensed or official data and avoids article screenshots.",
        ),
        _claim(
            "caveat",
            package.caveat,
            source_refs,
            "source_backed" if source_refs else "needs_source",
            "Keep uncertainty visible in the final edit.",
        ),
    ]
    return {
        "story_id": story.story_id,
        "status": _status(claims),
        "editorial_overrides": overrides,
        "claims": claims,
    }


def _claim(
    claim_id: str,
    text: str,
    source_refs: list[str],
    verification_status: str,
    editor_note: str,
) -> dict[str, object]:
    return {
        "claim_id": claim_id,
        "text": text,
        "source_refs": source_refs,
        "verification_status": verification_status,
        "editor_note": editor_note,
    }


def _status(claims: list[dict[str, object]]) -> str:
    if any(claim["verification_status"] in {"needs_source", "needs_primary_source"} for claim in claims):
        return "blocked"
    if any(claim["verification_status"] == "editor_verify" for claim in claims):
        return "needs_review"
    return "ready"


def _source_names(story: StoryCandidate) -> str:
    if story.primary_evidence:
        return ", ".join(item["source_name"] for item in story.primary_evidence)
    if story.source_trail:
        return ", ".join(item["source_name"] for item in story.source_trail[:2])
    return "source pending"


def _primary_evidence_status(primary_refs: list[str], editorial_overrides: list[dict[str, object]]) -> str:
    if primary_refs:
        return "source_backed"
    if has_override(editorial_overrides, "primary_source"):
        return "editor_verify"
    return "needs_primary_source"


def _primary_evidence_note(primary_refs: list[str], editorial_overrides: list[dict[str, object]]) -> str:
    if primary_refs:
        return "Confirm the linked source is official or first-party before publishing."
    if has_override(editorial_overrides, "primary_source"):
        return "Primary-source gap is editor-overridden; retain the override reason and evidence URL with the package."
    return "Attach a primary source or record an editor override before approval."
