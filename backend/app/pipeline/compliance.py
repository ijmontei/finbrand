from __future__ import annotations

import re

from app.claims import build_claim_checklist
from app.models import QAGate, StoryCandidate, VideoPackage
from app.overrides import has_override, serialize_overrides
from app.platform import build_platform_readiness
from app.rights import build_rights_report


BLOCKING_ADVICE_PATTERNS = [
    r"\byou should buy\b",
    r"\byou should sell\b",
    r"\bbuy this now\b",
    r"\bsell this now\b",
    r"\bguaranteed\b",
    r"\bcan'?t miss\b",
    r"\bwill 10x\b",
    r"\bprice target\b",
]


def run_qa(
    story: StoryCandidate,
    package: VideoPackage,
    editorial_overrides: list[dict[str, object]] | None = None,
    source_terms: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    overrides = serialize_overrides(editorial_overrides)
    gates = [
        _primary_source_gate(story, overrides),
        _advice_language_gate(package),
        _rights_gate(story, source_terms),
        _originality_gate(package),
        _platform_readiness_gate(story, package),
        _chart_gate(package),
        _caveat_gate(package),
        _claim_traceability_gate(story, package, overrides),
        _disclosure_gate(story),
    ]
    status = _overall_status(gates)
    return {
        "story_id": story.story_id,
        "status": status,
        "editorial_overrides": overrides,
        "gates": [gate.to_dict() for gate in gates],
    }


def _primary_source_gate(story: StoryCandidate, editorial_overrides: list[dict[str, object]]) -> QAGate:
    if story.primary_evidence:
        source_names = ", ".join(item["source_name"] for item in story.primary_evidence)
        return QAGate("Primary-source traceability", "pass", f"Primary evidence present: {source_names}.")
    if has_override(editorial_overrides, "primary_source"):
        return QAGate(
            "Primary-source traceability",
            "warn",
            "No primary source is attached, but an editor override is recorded for this story.",
        )
    return QAGate(
        "Primary-source traceability",
        "block",
        "No primary or first-party evidence is attached to this story.",
    )


def _advice_language_gate(package: VideoPackage) -> QAGate:
    text = " ".join([package.script_60s, package.caption, package.thumbnail_text]).lower()
    for pattern in BLOCKING_ADVICE_PATTERNS:
        if re.search(pattern, text):
            return QAGate("Advice-language risk", "block", f"Matched blocked pattern: {pattern}.")
    return QAGate("Advice-language risk", "pass", "No blocked personalized-advice phrases found.")


def _rights_gate(story: StoryCandidate, source_terms: list[dict[str, object]] | None = None) -> QAGate:
    report = build_rights_report(story, source_terms=source_terms)
    if report["status"] == "blocked":
        return QAGate("Rights hygiene", "block", "No publishable source-rights trail is attached.")
    if report["status"] == "needs_review":
        return QAGate("Rights hygiene", "warn", "One or more sources needs rights or redistribution review.")
    return QAGate("Rights hygiene", "pass", "Source-rights report is ready for editorial review.")


def _originality_gate(package: VideoPackage) -> QAGate:
    if package.why_it_matters and package.summary_bullets and len(package.script_60s.split()) >= 90:
        return QAGate("Original commentary", "pass", "Draft includes explanation beyond source recap.")
    return QAGate("Original commentary", "warn", "Draft needs more original explanation before publishing.")


def _platform_readiness_gate(story: StoryCandidate, package: VideoPackage) -> QAGate:
    report = build_platform_readiness(story, package)
    if report["status"] == "blocked":
        return QAGate("Platform originality", "block", "Draft looks too close to reused or commodity content.")
    if report["status"] == "needs_review":
        return QAGate("Platform originality", "warn", "Draft needs platform/originality review before publishing.")
    return QAGate("Platform originality", "pass", "Draft has original framing, owned visuals, and human judgment markers.")


def _chart_gate(package: VideoPackage) -> QAGate:
    if package.chart_idea:
        return QAGate("Visual explanation", "pass", "A single chart idea is attached.")
    return QAGate("Visual explanation", "warn", "No chart idea is attached.")


def _caveat_gate(package: VideoPackage) -> QAGate:
    if package.caveat:
        return QAGate("Uncertainty note", "pass", "Draft includes a caveat.")
    return QAGate("Uncertainty note", "warn", "Draft is missing a caveat.")


def _claim_traceability_gate(
    story: StoryCandidate,
    package: VideoPackage,
    editorial_overrides: list[dict[str, object]],
) -> QAGate:
    checklist = build_claim_checklist(story, package, editorial_overrides=editorial_overrides)
    if checklist["status"] == "blocked":
        return QAGate("Claim traceability", "block", "One or more material claims lacks source references.")
    if checklist["status"] == "needs_review":
        return QAGate("Claim traceability", "warn", "Material claims are listed for editor verification.")
    return QAGate("Claim traceability", "pass", "Material claims have source references.")


def _disclosure_gate(story: StoryCandidate) -> QAGate:
    if "sponsored" in story.risk_flags or "affiliate" in story.risk_flags:
        return QAGate("Disclosure readiness", "warn", "Sponsorship or affiliate flag needs explicit disclosure copy.")
    return QAGate("Disclosure readiness", "pass", "No compensation metadata is attached to this story.")


def _overall_status(gates: list[QAGate]) -> str:
    if any(gate.status == "block" for gate in gates):
        return "blocked"
    if any(gate.status == "warn" for gate in gates):
        return "needs_review"
    return "ready"
