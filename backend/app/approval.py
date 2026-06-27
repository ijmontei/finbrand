from __future__ import annotations

from app.claims import build_claim_checklist
from app.models import StoryCandidate, VideoPackage
from app.pipeline.compliance import run_qa
from app.platform import build_platform_readiness
from app.rights import build_rights_report


def build_approval_checklist(story: StoryCandidate, package: VideoPackage) -> dict[str, object]:
    qa = run_qa(story, package)
    claims = build_claim_checklist(story, package)
    rights = build_rights_report(story)
    platform = build_platform_readiness(story, package)
    checks = [
        _qa_check(qa),
        _claims_check(claims),
        _rights_check(rights),
        _platform_check(platform),
        _editor_accountability_check(qa, claims, rights, platform),
    ]
    status = _status(checks)
    return {
        "story_id": story.story_id,
        "status": status,
        "can_approve": status != "blocked",
        "notes_required": status == "needs_review",
        "checks": checks,
        "required_actions": _required_actions(checks),
        "publish_rule": "Approve only after blockers are cleared; warnings require editor notes that explain the human judgment call.",
    }


def _qa_check(qa: dict[str, object]) -> dict[str, object]:
    status = str(qa["status"])
    if status == "blocked":
        blockers = [gate["name"] for gate in qa["gates"] if gate["status"] == "block"]
        return _check(
            "qa_gates",
            "QA gates",
            "block",
            f"Blocked QA gates: {', '.join(blockers)}.",
            "Clear every blocking QA gate before approval.",
        )
    if status == "needs_review":
        warnings = [gate["name"] for gate in qa["gates"] if gate["status"] == "warn"]
        return _check(
            "qa_gates",
            "QA gates",
            "warn",
            f"QA warnings need editor review: {', '.join(warnings)}.",
            "Document why each warning is acceptable or revise the package.",
        )
    return _check("qa_gates", "QA gates", "pass", "All QA gates passed.", "Keep the QA snapshot with the package.")


def _claims_check(claims: dict[str, object]) -> dict[str, object]:
    status = str(claims["status"])
    if status == "blocked":
        return _check(
            "claim_traceability",
            "Claim traceability",
            "block",
            "One or more material claims needs a source.",
            "Attach source references for every material claim before approval.",
        )
    if status == "needs_review":
        return _check(
            "claim_traceability",
            "Claim traceability",
            "warn",
            "One or more claims needs editor verification.",
            "Verify dates, tickers, percentages, causal language, and chart framing.",
        )
    return _check(
        "claim_traceability",
        "Claim traceability",
        "pass",
        "Material claims have source references.",
        "Retain the claim checklist with the final export.",
    )


def _rights_check(rights: dict[str, object]) -> dict[str, object]:
    status = str(rights["status"])
    if status == "blocked":
        return _check(
            "source_rights",
            "Source rights",
            "block",
            "Source-rights trail is not publishable.",
            "Resolve missing source-rights notes before approval.",
        )
    if status == "needs_review":
        return _check(
            "source_rights",
            "Source rights",
            "warn",
            "At least one source needs rights or redistribution review.",
            "Confirm provider terms before showing raw source text or market-data values.",
        )
    return _check(
        "source_rights",
        "Source rights",
        "pass",
        "Source-rights report is ready.",
        "Use original commentary and short citations only.",
    )


def _platform_check(platform: dict[str, object]) -> dict[str, object]:
    status = str(platform["status"])
    if status == "blocked":
        return _check(
            "platform_readiness",
            "Platform readiness",
            "block",
            "Draft looks too close to reused or commodity content.",
            "Rewrite around original commentary and owned visuals before approval.",
        )
    if status == "needs_review":
        return _check(
            "platform_readiness",
            "Platform readiness",
            "warn",
            "Draft needs platform/originality review.",
            "Confirm the final cut adds commentary, transformation, and human judgment.",
        )
    return _check(
        "platform_readiness",
        "Platform readiness",
        "pass",
        "Draft has original framing and visual transformation markers.",
        "Confirm the rendered final cut preserves the original angle.",
    )


def _editor_accountability_check(
    qa: dict[str, object],
    claims: dict[str, object],
    rights: dict[str, object],
    platform: dict[str, object],
) -> dict[str, object]:
    statuses = {str(report["status"]) for report in [qa, claims, rights, platform]}
    if "blocked" in statuses:
        return _check(
            "editor_accountability",
            "Editor accountability",
            "block",
            "Approval is blocked until the package has no blocking checks.",
            "Use hold or revise until blockers are cleared.",
        )
    if "needs_review" in statuses:
        return _check(
            "editor_accountability",
            "Editor accountability",
            "warn",
            "Approval is allowed only with editor notes for the remaining warnings.",
            "Add notes describing the rights, claim, platform, or QA judgment behind approval.",
        )
    return _check(
        "editor_accountability",
        "Editor accountability",
        "pass",
        "Approval can be recorded without additional warning notes.",
        "Keep the decision ledger event as the final human signoff.",
    )


def _check(check_id: str, name: str, status: str, detail: str, action: str) -> dict[str, str]:
    return {
        "id": check_id,
        "name": name,
        "status": status,
        "detail": detail,
        "editorial_action": action,
    }


def _status(checks: list[dict[str, str]]) -> str:
    if any(check["status"] == "block" for check in checks):
        return "blocked"
    if any(check["status"] == "warn" for check in checks):
        return "needs_review"
    return "ready"


def _required_actions(checks: list[dict[str, str]]) -> list[str]:
    actions = []
    for check in checks:
        if check["status"] != "pass" and check["editorial_action"] not in actions:
            actions.append(check["editorial_action"])
    if not actions:
        actions.append("Record final human approval before rendering or publishing.")
    return actions
