from __future__ import annotations

import re
from collections.abc import Iterable

from app.models import StoryCandidate, VideoPackage


GENERIC_RECAP_PATTERNS = [
    r"\btop (financial|market|stock) headlines\b",
    r"\btoday'?s (financial|market|stock) news\b",
    r"\bhere are the headlines\b",
    r"\bnews roundup\b",
    r"\bquick recap\b",
]

ADVICE_PATTERNS = [
    r"\byou should buy\b",
    r"\byou should sell\b",
    r"\bbuy this now\b",
    r"\bsell this now\b",
    r"\bguaranteed\b",
    r"\bcan'?t miss\b",
    r"\bwill 10x\b",
    r"\bprice target\b",
]

STOP_WORDS = {
    "about",
    "after",
    "because",
    "before",
    "market",
    "markets",
    "moved",
    "moves",
    "news",
    "release",
    "report",
    "said",
    "says",
    "stock",
    "stocks",
    "story",
    "today",
    "with",
}


def build_platform_readiness(story: StoryCandidate, package: VideoPackage) -> dict[str, object]:
    checks = [
        _original_angle_check(story, package),
        _source_reuse_check(story, package),
        _visual_explanation_check(package),
        _human_judgment_check(package),
        _advice_check(package),
        _format_durability_check(package),
    ]
    required_actions = _required_actions(checks)
    score = round(sum(float(check["score"]) for check in checks) / len(checks), 2)
    status = _status(checks)
    return {
        "story_id": story.story_id,
        "status": status,
        "originality_score": score,
        "risk_level": _risk_level(status, score),
        "checks": checks,
        "required_actions": required_actions,
        "platform_guidance": {
            "youtube_shorts": "Publish only after the draft adds original commentary, data visualization, and human editorial judgment beyond source recap.",
            "instagram_reels": "Use transformed visuals and commentary; avoid reposted article text, unedited screenshots, or templated headline narration.",
        },
        "publish_rule": "Use automation to draft the research packet; publish only a human-approved, source-cited, visually transformed explanation.",
    }


def _original_angle_check(story: StoryCandidate, package: VideoPackage) -> dict[str, object]:
    has_angle = bool(story.angles)
    has_explanation = bool(package.why_it_matters and len(package.why_it_matters.split()) >= 10)
    has_causal_hook = bool(re.search(r"\b(because|why|what|data|evidence|reaction)\b", package.hook.lower()))
    passed = has_angle and has_explanation and has_causal_hook
    return _check(
        "original_angle",
        "Original analytical angle",
        "pass" if passed else "warn",
        1.0 if passed else 0.55,
        "Draft frames the story around a data-backed explanation." if passed else "Add a clearer analytical angle beyond the source headline.",
        "Rewrite the hook around what the market misread, what changed, or what the data proves.",
    )


def _source_reuse_check(story: StoryCandidate, package: VideoPackage) -> dict[str, object]:
    title_tokens = [_tokens(item.get("title", "")) for item in story.source_trail]
    draft_text = " ".join([package.hook, package.caption, package.thumbnail_text, package.script_60s])
    draft_tokens = _tokens(draft_text)
    max_overlap = max((_overlap(title, draft_tokens) for title in title_tokens), default=0.0)
    recap_pattern = _first_match(GENERIC_RECAP_PATTERNS, draft_text)
    if recap_pattern:
        return _check(
            "source_reuse",
            "Source reuse risk",
            "block",
            0.0,
            f"Draft matched a commodity recap pattern: {recap_pattern}.",
            "Replace headline-roundup framing with an original explanation and short source citations.",
        )
    if max_overlap >= 0.72:
        return _check(
            "source_reuse",
            "Source reuse risk",
            "warn",
            0.45,
            "Draft wording is close to a source title.",
            "Paraphrase in the brand voice and cite the source instead of echoing its headline.",
        )
    return _check(
        "source_reuse",
        "Source reuse risk",
        "pass",
        1.0,
        "No obvious headline-reuse or commodity recap pattern found.",
        "Keep source excerpts short and link to the original source.",
    )


def _visual_explanation_check(package: VideoPackage) -> dict[str, object]:
    visual_assets = package.asset_manifest.get("visual_assets", [])
    charts = package.asset_manifest.get("charts", [])
    has_chart = bool(package.chart_idea)
    has_assets = (isinstance(visual_assets, list) and bool(visual_assets)) or (
        isinstance(charts, list) and bool(charts)
    )
    passed = has_chart and has_assets
    return _check(
        "visual_explanation",
        "Visual transformation",
        "pass" if passed else "warn",
        1.0 if passed else 0.55,
        "Draft includes a chart concept and renderable visual assets." if passed else "Draft needs a clear owned visual explanation.",
        "Attach a chart, data annotation, or storyboard beat that explains the signal without article screenshots.",
    )


def _human_judgment_check(package: VideoPackage) -> dict[str, object]:
    has_caveat = bool(package.caveat)
    has_watch_next = bool(
        re.search(
            r"\b(watch|caveat|not yet known|does not prove|uncertain|still needs checking)\b",
            package.script_60s.lower(),
        )
    )
    passed = has_caveat and has_watch_next
    return _check(
        "human_judgment",
        "Human-like judgment",
        "pass" if passed else "warn",
        1.0 if passed else 0.6,
        "Draft includes caveat language and what to watch next." if passed else "Draft needs explicit uncertainty or watch-next judgment.",
        "Add a caveat that says what is not yet known and what evidence would confirm the story.",
    )


def _advice_check(package: VideoPackage) -> dict[str, object]:
    text = " ".join([package.script_60s, package.caption, package.thumbnail_text]).lower()
    pattern = _first_match(ADVICE_PATTERNS, text)
    if pattern:
        return _check(
            "advice_language",
            "Platform and finance language",
            "block",
            0.0,
            f"Draft matched blocked advice language: {pattern}.",
            "Remove personalized advice, price-target, guarantee, or hype phrasing.",
        )
    return _check(
        "advice_language",
        "Platform and finance language",
        "pass",
        1.0,
        "No blocked personalized-advice phrases found.",
        "Keep framing educational and analytical.",
    )


def _format_durability_check(package: VideoPackage) -> dict[str, object]:
    word_count = len(package.script_60s.split())
    has_required_parts = all(
        [
            package.hook,
            len(package.summary_bullets) >= 3,
            package.why_it_matters,
            package.chart_idea,
            package.caveat,
            package.caption,
            package.thumbnail_text,
        ]
    )
    if word_count < 105:
        return _check(
            "format_durability",
            "Short-form format durability",
            "warn",
            0.5,
            f"Script is only {word_count} words, which may read as a thin recap.",
            "Expand with one extra explanatory sentence or a sharper caveat.",
        )
    return _check(
        "format_durability",
        "Short-form format durability",
        "pass" if has_required_parts else "warn",
        1.0 if has_required_parts else 0.6,
        "Draft has a full hook, summary, visual, caveat, caption, and thumbnail package."
        if has_required_parts
        else "Draft is missing one or more expected short-form package elements.",
        "Keep the recurring format, but vary the substance and angle for each story.",
    )


def _check(
    check_id: str,
    name: str,
    status: str,
    score: float,
    detail: str,
    editorial_action: str,
) -> dict[str, object]:
    return {
        "id": check_id,
        "name": name,
        "status": status,
        "score": score,
        "detail": detail,
        "editorial_action": editorial_action,
    }


def _tokens(text: object) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", str(text).lower())
        if len(token) > 3 and token not in STOP_WORDS
    }


def _overlap(source_tokens: set[str], draft_tokens: set[str]) -> float:
    if not source_tokens:
        return 0.0
    return len(source_tokens & draft_tokens) / len(source_tokens)


def _first_match(patterns: Iterable[str], text: str) -> str | None:
    lowered = text.lower()
    for pattern in patterns:
        if re.search(pattern, lowered):
            return pattern
    return None


def _required_actions(checks: list[dict[str, object]]) -> list[str]:
    actions = []
    for check in checks:
        if check["status"] != "pass":
            action = str(check["editorial_action"])
            if action not in actions:
                actions.append(action)
    if not actions:
        actions.append("Editor should confirm the final cut still adds original commentary and owned visuals.")
    return actions


def _status(checks: list[dict[str, object]]) -> str:
    if any(check["status"] == "block" for check in checks):
        return "blocked"
    if any(check["status"] == "warn" for check in checks):
        return "needs_review"
    return "ready"


def _risk_level(status: str, score: float) -> str:
    if status == "blocked" or score < 0.55:
        return "high"
    if status == "needs_review" or score < 0.82:
        return "medium"
    return "low"
