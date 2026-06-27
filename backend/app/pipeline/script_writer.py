from __future__ import annotations

from app.models import StoryCandidate, VideoPackage


FORMAT_PLAYBOOK = {
    "data_missed": {
        "name": "The Story Everyone Saw vs. The Data Everyone Missed",
        "variant": "contrast-led explainer",
    },
    "why_it_moved": {
        "name": "Why This Moved in 60 Seconds",
        "variant": "cause-and-effect brief",
    },
    "market_misread": {
        "name": "The Market Misread This Story",
        "variant": "contrarian context",
    },
    "three_signals": {
        "name": "3 Signals That Explain Today",
        "variant": "chart-led rundown",
    },
}

FORMAT_BY_STORY_TYPE = {
    "single_stock_filing": ["why_it_moved", "data_missed"],
    "macro_release": ["data_missed", "three_signals"],
    "fed_policy": ["market_misread", "data_missed"],
    "earnings_followthrough": ["market_misread", "why_it_moved"],
}


def generate_video_package(story: StoryCandidate) -> VideoPackage:
    entity = story.primary_entity["name"]
    ticker = story.primary_entity["ticker"]
    move = story.metrics.get("price_change_pct", 0)
    volume = story.metrics.get("volume_vs_20d", 1)
    source = _source_phrase(story)
    format_key, format_name, style_variant = _select_format(story)
    angle = _editorial_angle(story, entity, source, format_key)
    hook = _hook(story, entity, move, format_key)
    bullets = _bullets(story, entity, move, volume, source, format_key)
    why = _why_it_matters(story, entity)
    chart = _chart_idea(story, ticker)
    caveat = _caveat(story)
    script = _script(format_key, hook, bullets, why, caveat, chart)
    caption = _caption(story, source, format_name)
    thumbnail = _thumbnail_text(story, entity)
    return VideoPackage(
        story_id=story.story_id,
        hook=hook,
        summary_bullets=bullets,
        why_it_matters=why,
        chart_idea=chart,
        caveat=caveat,
        script_60s=script,
        caption=caption,
        thumbnail_text=thumbnail,
        risk_flags=story.risk_flags,
        asset_manifest=_asset_manifest(story, chart, format_key, format_name, style_variant),
        format_key=format_key,
        format_name=format_name,
        style_variant=style_variant,
        editorial_angle=angle,
    )


def _select_format(story: StoryCandidate) -> tuple[str, str, str]:
    candidates = FORMAT_BY_STORY_TYPE.get(story.story_type, list(FORMAT_PLAYBOOK))
    selection_basis = f"{story.story_id}:{story.headline}:{story.primary_entity.get('ticker', '')}"
    checksum = sum(ord(char) for char in selection_basis)
    format_key = candidates[checksum % len(candidates)]
    profile = FORMAT_PLAYBOOK[format_key]
    return format_key, profile["name"], profile["variant"]


def _editorial_angle(story: StoryCandidate, entity: str, source: str, format_key: str) -> str:
    if format_key == "data_missed":
        return f"Separate the visible {entity} move from the evidence the market is actually repricing."
    if format_key == "why_it_moved":
        return f"Explain the trigger, market reaction, and source trail behind the {entity} move."
    if format_key == "market_misread":
        return f"Challenge the first-read narrative by checking what {source} actually confirms."
    if format_key == "three_signals":
        return "Use three quick signals: price reaction, volume context, and the official source trail."
    return "Explain the market reaction with source-backed context and one clear caveat."


def _source_phrase(story: StoryCandidate) -> str:
    if story.primary_evidence:
        return story.primary_evidence[0]["source_name"]
    if story.source_trail:
        return story.source_trail[0]["source_name"]
    return "source review pending"


def _hook(story: StoryCandidate, entity: str, move: object, format_key: str) -> str:
    if format_key == "data_missed":
        return f"Everyone saw the {entity} move. The missed part is the data behind it."
    if format_key == "why_it_moved" and story.story_type == "single_stock_filing":
        return f"{entity} moved because a formal filing changed the evidence trail."
    if format_key == "why_it_moved":
        return f"{entity} moved, but the useful question is why the market cared."
    if format_key == "market_misread" and story.story_type == "fed_policy":
        return "The Fed story today is less about drama and more about wording."
    if format_key == "market_misread":
        return f"{entity} is a good reminder that a beat is not the whole story."
    if format_key == "three_signals":
        return f"Three signals explain why {entity} is in focus today."
    return f"{entity} moved {move}% because the market found a cleaner signal than the headline."


def _bullets(
    story: StoryCandidate,
    entity: str,
    move: object,
    volume: object,
    source: str,
    format_key: str,
) -> list[str]:
    setup = story.story_type.replace("_", " ")
    if format_key == "data_missed":
        return [
            f"The surface story is {entity} in a {setup} setup.",
            f"The market signal is {move}% price action with volume near {volume} times normal.",
            f"The missing context comes from {source}, not just headline velocity.",
        ]
    if format_key == "market_misread":
        return [
            f"The first read is {entity} in a {setup} setup.",
            f"The reaction is {move}% with volume near {volume} times normal.",
            f"The source to check before overreading it is {source}.",
        ]
    if format_key == "three_signals":
        return [
            f"Signal one: {entity} is tied to a {setup} setup.",
            f"Signal two: price moved {move}% with volume near {volume} times normal.",
            f"Signal three: {source} is the strongest source in the packet.",
        ]
    return [
        f"{entity} is tied to a {setup} setup.",
        f"The visible market reaction is {move}% with volume near {volume} times normal.",
        f"The strongest source in the packet is {source}.",
    ]


def _why_it_matters(story: StoryCandidate, entity: str) -> str:
    if story.story_type in {"macro_release", "fed_policy"}:
        return "Rates, risk appetite, and sector leadership can all reprice when the official data changes the path."
    if story.story_type == "single_stock_filing":
        return "A filing moves the story from rumor or interpretation into a dated disclosure investors can verify."
    if story.story_type == "earnings_followthrough":
        return "The market is separating headline growth from durability, margins, and what management can repeat next quarter."
    return f"The point is not that {entity} moved. The point is whether the move is supported by data the market can keep pricing."


def _chart_idea(story: StoryCandidate, ticker: str) -> str:
    if story.story_type == "macro_release":
        return "Line chart: latest macro print versus 2-year Treasury yield reaction."
    if story.story_type == "fed_policy":
        return "Timeline chart: 2-year yield and index reaction around the statement window."
    if story.story_type == "single_stock_filing":
        return f"Annotated price-volume chart for {ticker} with the filing timestamp."
    if story.story_type == "earnings_followthrough":
        return f"Two-panel chart: {ticker} price reaction above trailing revenue or margin trend."
    return f"Normalized intraday chart comparing {ticker} with its closest sector ETF."


def _caveat(story: StoryCandidate) -> str:
    if "needs_primary_source_review" in story.risk_flags:
        return "The causal link is not ready for publication until an editor verifies a primary or first-party source."
    if story.story_type == "macro_release":
        return "One print does not make a trend, so the next release and component details still matter."
    if story.story_type == "fed_policy":
        return "The first reaction after a Fed release can reverse by the close."
    return "The move explains what the market is reacting to today, not what the asset is worth."


def _script(format_key: str, hook: str, bullets: list[str], why: str, caveat: str, chart: str) -> str:
    lines = [
        hook,
        bullets[0],
        bullets[1],
        bullets[2],
        why,
        _bridge_line(format_key),
        caveat,
        f"The clean visual is simple: {chart}",
        _close_line(format_key),
    ]
    return "\n".join(lines)


def _bridge_line(format_key: str) -> str:
    if format_key == "data_missed":
        return "That gap between the visible story and the confirming data is the reason this is worth explaining."
    if format_key == "market_misread":
        return "The point is to slow down the first take before it turns into a lazy market narrative."
    if format_key == "three_signals":
        return "Put together, those three signals are stronger than a headline recap by itself."
    return "That is why this belongs in a market-reaction slate instead of a headline recap."


def _close_line(format_key: str) -> str:
    if format_key == "three_signals":
        return "This is not a recommendation. It is a quick map of the signals, the source, and what still needs checking."
    if format_key == "market_misread":
        return "This is not a recommendation. It is a check on the story the market may be telling itself."
    return "This is not a recommendation. It is a map of what moved, what confirmed it, and what still needs checking."


def _caption(story: StoryCandidate, source: str, format_name: str) -> str:
    return f"{format_name}: {story.headline}. Source trail: {source}. Not investment advice."


def _thumbnail_text(story: StoryCandidate, entity: str) -> str:
    if story.story_type in {"macro_release", "fed_policy"}:
        return "The Number That Moved Rates"
    if story.story_type == "single_stock_filing":
        return "The Filing Behind The Move"
    return f"Why {entity} Moved"


def _asset_manifest(
    story: StoryCandidate,
    chart: str,
    format_key: str,
    format_name: str,
    style_variant: str,
) -> dict[str, object]:
    return {
        "asset_bundle_id": f"bundle_{story.story_id.replace('story_', '')}",
        "story_id": story.story_id,
        "format": "vertical_1080x1920_60s",
        "editorial_format": {
            "key": format_key,
            "name": format_name,
            "style_variant": style_variant,
        },
        "script_ref": f"script_{story.story_id}",
        "storyboard_ref": "storyboard.json",
        "preview_ref": "preview.html",
        "voiceover": {
            "mode": "manual_or_tts",
            "duration_target_sec": 60,
        },
        "charts": [
            {
                "chart_id": "chart_1",
                "type": "editorial_signal_chart",
                "description": chart,
                "image_ref": "chart_signal.svg",
            }
        ],
        "captions": {
            "format": "srt_or_burned_in",
            "srt_ref": "captions.srt",
            "burned_in": True,
        },
        "video_outputs": [
            {"platform": "youtube_shorts", "size": "1080x1920"},
            {"platform": "instagram_reels", "size": "1080x1920"},
            {"platform": "tiktok", "size": "1080x1920"},
        ],
    }
