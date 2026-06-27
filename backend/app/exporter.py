from __future__ import annotations

import json
from pathlib import Path

from app.approval import build_approval_checklist
from app.charts import render_signal_chart_svg
from app.claims import build_claim_checklist
from app.models import StoryCandidate, VideoPackage
from app.pipeline.compliance import run_qa
from app.pipeline.script_writer import generate_video_package
from app.platform import build_platform_readiness
from app.render_plan import build_storyboard, generate_srt, render_preview_html
from app.rights import build_rights_report


def export_story_package(story: StoryCandidate, output_dir: Path) -> dict[str, str]:
    package = generate_video_package(story)
    qa = run_qa(story, package)
    storyboard = build_storyboard(story, package)
    claims = build_claim_checklist(story, package)
    rights = build_rights_report(story)
    platform = build_platform_readiness(story, package)
    approval = build_approval_checklist(story, package)
    story_dir = output_dir / story.story_id
    story_dir.mkdir(parents=True, exist_ok=True)

    files = {
        "story": story_dir / "story.json",
        "package": story_dir / "package.json",
        "qa": story_dir / "qa.json",
        "claims": story_dir / "claims.json",
        "rights": story_dir / "rights_report.json",
        "platform": story_dir / "platform_readiness.json",
        "approval": story_dir / "approval_checklist.json",
        "manifest": story_dir / "asset_manifest.json",
        "chart": story_dir / "chart_signal.svg",
        "storyboard": story_dir / "storyboard.json",
        "captions": story_dir / "captions.srt",
        "preview": story_dir / "preview.html",
        "decision_template": story_dir / "decision_template.json",
        "brief": story_dir / "editor_brief.md",
    }
    _write_json(files["story"], story.to_dict())
    _write_json(files["package"], package.to_dict())
    _write_json(files["qa"], qa)
    _write_json(files["claims"], claims)
    _write_json(files["rights"], rights)
    _write_json(files["platform"], platform)
    _write_json(files["approval"], approval)
    _write_json(files["manifest"], package.asset_manifest)
    _write_json(files["storyboard"], storyboard)
    files["chart"].write_text(render_signal_chart_svg(story), encoding="utf-8")
    files["captions"].write_text(generate_srt(package), encoding="utf-8")
    files["preview"].write_text(render_preview_html(story, package, storyboard, qa), encoding="utf-8")
    _write_json(files["decision_template"], _decision_template(story, qa, approval))
    files["brief"].write_text(_editor_brief(story, package, qa, claims, rights, platform, approval), encoding="utf-8")
    return {name: str(path) for name, path in files.items()}


def export_story_slate(stories: list[StoryCandidate], output_dir: Path, limit: int = 5) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    selected = stories[:limit]
    slate = {
        "count": len(selected),
        "stories": [story.to_dict() for story in selected],
    }
    slate_path = output_dir / "slate.json"
    _write_json(slate_path, slate)
    package_files = [export_story_package(story, output_dir) for story in selected]
    return {
        "slate": str(slate_path),
        "packages": package_files,
    }


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _editor_brief(
    story: StoryCandidate,
    package: VideoPackage,
    qa: dict[str, object],
    claims: dict[str, object],
    rights: dict[str, object],
    platform: dict[str, object],
    approval: dict[str, object],
) -> str:
    source_lines = "\n".join(
        f"- {item['source_name']}: {item['title']} ({item['url']})" for item in story.source_trail
    )
    bullets = "\n".join(f"- {bullet}" for bullet in package.summary_bullets)
    gates = "\n".join(
        f"- {gate['status'].upper()}: {gate['name']} - {gate['detail']}" for gate in qa["gates"]
    )
    claim_lines = "\n".join(
        f"- {claim['verification_status'].upper()}: {claim['text']}" for claim in claims["claims"]
    )
    rights_lines = "\n".join(
        f"- {source['risk_level'].upper()}: {source['source_name']} - {source['review_action']}"
        for source in rights["sources"]
    )
    platform_lines = "\n".join(
        f"- {check['status'].upper()}: {check['name']} - {check['detail']}" for check in platform["checks"]
    )
    approval_lines = "\n".join(
        f"- {check['status'].upper()}: {check['name']} - {check['detail']}" for check in approval["checks"]
    )
    return f"""# {story.headline}

Status: {story.editorial_state}
QA: {qa["status"]}
Score: {story.scores["story_score"]}

## Hook

{package.hook}

## Editorial Format

Format: {package.format_name}
Style: {package.style_variant}
Angle: {package.editorial_angle}

## Summary

{bullets}

## Why It Matters

{package.why_it_matters}

## Chart

{package.chart_idea}

## Render Plan

- Storyboard: `storyboard.json`
- Captions: `captions.srt`
- Chart asset: `chart_signal.svg`
- Preview: `preview.html`
- Decision template: `decision_template.json`

## Caveat

{package.caveat}

## 60s Script

{package.script_60s}

## Source Trail

{source_lines}

## Claim Checklist

{claim_lines}

## Rights Report

Status: {rights["status"]}

{rights_lines}

## Platform Readiness

Status: {platform["status"]}
Originality score: {platform["originality_score"]}
Risk level: {platform["risk_level"]}

{platform_lines}

## Approval Checklist

Status: {approval["status"]}
Can approve: {approval["can_approve"]}
Notes required: {approval["notes_required"]}

{approval_lines}

## QA Gates

{gates}
"""


def _decision_template(story: StoryCandidate, qa: dict[str, object], approval: dict[str, object]) -> dict[str, object]:
    return {
        "story_id": story.story_id,
        "decision": "pending",
        "allowed_decisions": ["approve", "hold", "revise", "archive"],
        "editor": "",
        "notes": "",
        "qa_status": qa["status"],
        "approval_status": approval["status"],
        "can_approve": approval["can_approve"],
        "approval_notes_required": approval["notes_required"],
        "story_score": story.scores["story_score"],
        "required_before_publish": [
            "confirm approval checklist has no blockers",
            "confirm factual claims",
            "confirm source links and usage rights",
            "confirm no personalized investment advice",
            "confirm chart data and visual framing",
            "confirm disclosure language if compensation exists",
        ],
    }
