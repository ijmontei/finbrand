from __future__ import annotations

from app.models import StoryCandidate, VideoPackage


def build_publish_packet(
    story: StoryCandidate,
    package: VideoPackage,
    qa: dict[str, object],
    claims: dict[str, object],
    rights: dict[str, object],
    platform: dict[str, object],
    approval: dict[str, object],
    decision: dict[str, object],
) -> dict[str, object]:
    blockers = _blockers(qa, claims, rights, platform, approval, decision)
    warnings = _warnings(qa, claims, rights, platform, approval)
    return {
        "story_id": story.story_id,
        "status": "blocked" if blockers else "ready_manual_publish",
        "publish_mode": "manual_only",
        "auto_post_allowed": False,
        "manual_publish_rule": "Use this packet for human-operated publishing only after final review; do not auto-post.",
        "blockers": blockers,
        "warnings": warnings,
        "decision": decision,
        "content": {
            "title": _title(story, package),
            "hook": package.hook,
            "script_60s": package.script_60s,
            "caption": package.caption,
            "thumbnail_text": package.thumbnail_text,
            "caveat": package.caveat,
            "disclaimer": "This is not personalized investment advice.",
        },
        "platform_variants": _platform_variants(story, package),
        "source_citations": _source_citations(story),
        "required_assets": [
            "chart_signal.svg",
            "captions.srt",
            "storyboard.json",
            "preview.html",
            "asset_manifest.json",
        ],
        "final_checklist": [
            "Confirm approved editor decision and notes are attached.",
            "Confirm no blocking QA, claims, rights, platform, or approval status remains.",
            "Confirm source links, terms status, and any provider restrictions.",
            "Confirm chart data and caption timing in the rendered preview.",
            "Confirm no personalized advice, price target, or compensation omission.",
            "Publish manually; archive final URL and performance metrics after posting.",
        ],
        "review_snapshot": {
            "qa_status": qa["status"],
            "claims_status": claims["status"],
            "rights_status": rights["status"],
            "platform_status": platform["status"],
            "approval_status": approval["status"],
            "approval_notes_required": approval["notes_required"],
            "source_terms_statuses": _source_terms_statuses(rights),
            "editorial_overrides": approval.get("editorial_overrides", []),
        },
    }


def render_publish_brief(packet: dict[str, object]) -> str:
    content = packet["content"]
    decision = packet["decision"]
    blockers = "\n".join(f"- {item}" for item in packet["blockers"]) or "- None"
    warnings = "\n".join(f"- {item}" for item in packet["warnings"]) or "- None"
    sources = "\n".join(
        f"- {source['source_name']}: {source['title']} ({source['url']})"
        for source in packet["source_citations"]
    )
    checklist = "\n".join(f"- {item}" for item in packet["final_checklist"])
    return f"""# Publish Packet: {content["title"]}

Status: {packet["status"]}
Mode: {packet["publish_mode"]}
Auto-post allowed: {packet["auto_post_allowed"]}

{packet["manual_publish_rule"]}

## Editor Decision

Decision: {decision.get("decision")}
Editor: {decision.get("editor")}
Notes: {decision.get("notes")}

## Blockers

{blockers}

## Warnings

{warnings}

## Caption

{content["caption"]}

## Script

{content["script_60s"]}

## Sources

{sources}

## Final Checklist

{checklist}
"""


def _blockers(
    qa: dict[str, object],
    claims: dict[str, object],
    rights: dict[str, object],
    platform: dict[str, object],
    approval: dict[str, object],
    decision: dict[str, object],
) -> list[str]:
    blockers = []
    if decision.get("decision") != "approve":
        blockers.append("Editor decision must be approve before a publish packet is ready.")
    if approval["status"] == "blocked" or not approval["can_approve"]:
        blockers.append("Approval checklist is blocked.")
    if approval["notes_required"] and not str(decision.get("notes", "")).strip():
        blockers.append("Approval notes are required for warning-level packages.")
    for label, report in [
        ("QA", qa),
        ("Claims", claims),
        ("Rights", rights),
        ("Platform", platform),
    ]:
        if report["status"] == "blocked":
            blockers.append(f"{label} status is blocked.")
    return blockers


def _warnings(
    qa: dict[str, object],
    claims: dict[str, object],
    rights: dict[str, object],
    platform: dict[str, object],
    approval: dict[str, object],
) -> list[str]:
    warnings = []
    for label, report in [
        ("QA", qa),
        ("Claims", claims),
        ("Rights", rights),
        ("Platform", platform),
        ("Approval", approval),
    ]:
        if report["status"] == "needs_review":
            warnings.append(f"{label} status needs review; retain editor notes with the published asset.")
    return warnings


def _title(story: StoryCandidate, package: VideoPackage) -> str:
    if package.thumbnail_text:
        return package.thumbnail_text
    return story.headline


def _platform_variants(story: StoryCandidate, package: VideoPackage) -> dict[str, object]:
    ticker = story.primary_entity.get("ticker", "MARKET")
    return {
        "youtube_shorts": {
            "title": _title(story, package),
            "description": f"{package.caption}\n\nNot personalized investment advice. Sources and caveats checked before publishing.",
            "tags": [ticker, "markets", "finance", "market commentary"],
        },
        "instagram_reels": {
            "caption": f"{package.caption}\n\nNot personalized investment advice. #{ticker} #markets #finance",
            "cover_text": package.thumbnail_text,
        },
    }


def _source_citations(story: StoryCandidate) -> list[dict[str, object]]:
    return [
        {
            "source_name": item["source_name"],
            "source_type": item["source_type"],
            "title": item["title"],
            "url": item["url"],
            "primary_source": item["primary_source"],
            "license_notes": item["license_notes"],
        }
        for item in story.source_trail
    ]


def _source_terms_statuses(rights: dict[str, object]) -> list[dict[str, object]]:
    return [
        {
            "source_name": source["source_name"],
            "posture": source["posture"],
            "terms_status": source["terms_status"],
            "restrictions": source["terms_restrictions"],
        }
        for source in rights["sources"]
    ]
