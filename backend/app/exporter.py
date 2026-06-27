from __future__ import annotations

import json
from pathlib import Path

from app.charts import render_signal_chart_svg
from app.models import StoryCandidate, VideoPackage
from app.pipeline.compliance import run_qa
from app.pipeline.script_writer import generate_video_package


def export_story_package(story: StoryCandidate, output_dir: Path) -> dict[str, str]:
    package = generate_video_package(story)
    qa = run_qa(story, package)
    story_dir = output_dir / story.story_id
    story_dir.mkdir(parents=True, exist_ok=True)

    files = {
        "story": story_dir / "story.json",
        "package": story_dir / "package.json",
        "qa": story_dir / "qa.json",
        "manifest": story_dir / "asset_manifest.json",
        "chart": story_dir / "chart_signal.svg",
        "brief": story_dir / "editor_brief.md",
    }
    _write_json(files["story"], story.to_dict())
    _write_json(files["package"], package.to_dict())
    _write_json(files["qa"], qa)
    _write_json(files["manifest"], package.asset_manifest)
    files["chart"].write_text(render_signal_chart_svg(story), encoding="utf-8")
    files["brief"].write_text(_editor_brief(story, package, qa), encoding="utf-8")
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


def _editor_brief(story: StoryCandidate, package: VideoPackage, qa: dict[str, object]) -> str:
    source_lines = "\n".join(
        f"- {item['source_name']}: {item['title']} ({item['url']})" for item in story.source_trail
    )
    bullets = "\n".join(f"- {bullet}" for bullet in package.summary_bullets)
    gates = "\n".join(
        f"- {gate['status'].upper()}: {gate['name']} - {gate['detail']}" for gate in qa["gates"]
    )
    return f"""# {story.headline}

Status: {story.editorial_state}
QA: {qa["status"]}
Score: {story.scores["story_score"]}

## Hook

{package.hook}

## Summary

{bullets}

## Why It Matters

{package.why_it_matters}

## Chart

{package.chart_idea}

## Caveat

{package.caveat}

## 60s Script

{package.script_60s}

## Source Trail

{source_lines}

## QA Gates

{gates}
"""
