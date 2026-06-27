from __future__ import annotations

import json
from pathlib import Path

from app.approval import build_approval_checklist
from app.models import StoryCandidate
from app.pipeline.script_writer import generate_video_package
from app.rights import build_rights_report


def build_daily_brief(
    stories: list[StoryCandidate],
    limit: int = 3,
    overrides_by_story: dict[str, list[dict[str, object]]] | None = None,
    source_terms: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    selected = stories[:limit]
    override_map = overrides_by_story or {}
    items = [_brief_item(story, override_map.get(story.story_id, []), source_terms) for story in selected]
    return {
        "title": "Market Signal Daily Brief",
        "subject": _subject_line(items),
        "count": len(items),
        "items": items,
        "editor_note": "Use this as an owned-audience brief: original commentary, short citations, no republished article text.",
        "compliance_note": "Educational market commentary only. Not personalized investment advice.",
    }


def export_daily_brief(
    stories: list[StoryCandidate],
    output_dir: Path,
    limit: int = 3,
    overrides_by_story: dict[str, list[dict[str, object]]] | None = None,
    source_terms: list[dict[str, object]] | None = None,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    brief = build_daily_brief(
        stories,
        limit=limit,
        overrides_by_story=overrides_by_story,
        source_terms=source_terms,
    )
    json_path = output_dir / "daily_brief.json"
    markdown_path = output_dir / "daily_brief.md"
    json_path.write_text(json.dumps(brief, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(render_daily_brief_markdown(brief), encoding="utf-8")
    return {
        "newsletter_json": str(json_path),
        "newsletter_markdown": str(markdown_path),
    }


def render_daily_brief_markdown(brief: dict[str, object]) -> str:
    items = brief.get("items", [])
    item_sections = "\n\n".join(_item_markdown(item, index) for index, item in enumerate(items, start=1))
    return f"""# {brief["title"]}

Subject: {brief["subject"]}

{brief["editor_note"]}

## Top Signals

{item_sections}

## Compliance Note

{brief["compliance_note"]}
"""


def _brief_item(
    story: StoryCandidate,
    editorial_overrides: list[dict[str, object]],
    source_terms: list[dict[str, object]] | None,
) -> dict[str, object]:
    package = generate_video_package(story)
    approval = build_approval_checklist(
        story,
        package,
        editorial_overrides=editorial_overrides,
        source_terms=source_terms,
    )
    rights = build_rights_report(story, source_terms=source_terms)
    return {
        "story_id": story.story_id,
        "headline": story.headline,
        "ticker": story.primary_entity.get("ticker", "MARKET"),
        "entity": story.primary_entity.get("name", "Market Story"),
        "story_score": story.scores["story_score"],
        "format": package.format_name,
        "hook": package.hook,
        "signal": package.summary_bullets[1] if len(package.summary_bullets) > 1 else package.hook,
        "why_it_matters": package.why_it_matters,
        "chart_to_watch": package.chart_idea,
        "caveat": package.caveat,
        "approval_status": approval["status"],
        "rights_status": rights["status"],
        "editorial_overrides": editorial_overrides,
        "source_refs": _source_refs(story),
    }


def _source_refs(story: StoryCandidate) -> list[dict[str, object]]:
    refs = []
    for item in story.source_trail[:3]:
        refs.append(
            {
                "source_name": item["source_name"],
                "title": item["title"],
                "url": item["url"],
                "primary_source": item["primary_source"],
            }
        )
    return refs


def _subject_line(items: list[dict[str, object]]) -> str:
    if not items:
        return "No publishable market signals yet"
    tickers = [str(item["ticker"]) for item in items[:3]]
    return "Market signals to watch: " + ", ".join(tickers)


def _item_markdown(item: object, index: int) -> str:
    if not isinstance(item, dict):
        return ""
    sources = "\n".join(
        f"- {source['source_name']}: [{source['title']}]({source['url']})"
        for source in item.get("source_refs", [])
        if isinstance(source, dict)
    )
    return f"""### {index}. {item["headline"]}

Format: {item["format"]}  
Ticker: `{item["ticker"]}`  
Editorial status: approval `{item["approval_status"]}`, rights `{item["rights_status"]}`
Overrides: {len(item.get("editorial_overrides", []))}

**Hook:** {item["hook"]}

**Signal:** {item["signal"]}

**Why It Matters:** {item["why_it_matters"]}

**Chart To Watch:** {item["chart_to_watch"]}

**Caveat:** {item["caveat"]}

**Sources**

{sources}
"""
