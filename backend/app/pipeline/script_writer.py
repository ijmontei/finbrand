from __future__ import annotations

from app.models import StoryCandidate, VideoPackage


def generate_video_package(story: StoryCandidate) -> VideoPackage:
    entity = story.primary_entity["name"]
    ticker = story.primary_entity["ticker"]
    move = story.metrics.get("price_change_pct", 0)
    volume = story.metrics.get("volume_vs_20d", 1)
    source = _source_phrase(story)
    hook = _hook(story, entity, move)
    bullets = _bullets(story, entity, move, volume, source)
    why = _why_it_matters(story, entity)
    chart = _chart_idea(story, ticker)
    caveat = _caveat(story)
    script = _script(hook, bullets, why, caveat, chart)
    caption = f"{story.headline}. Source trail: {source}. Not investment advice."
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
        asset_manifest=_asset_manifest(story, chart),
    )


def _source_phrase(story: StoryCandidate) -> str:
    if story.primary_evidence:
        return story.primary_evidence[0]["source_name"]
    if story.source_trail:
        return story.source_trail[0]["source_name"]
    return "source review pending"


def _hook(story: StoryCandidate, entity: str, move: object) -> str:
    if story.story_type == "macro_release":
        return "The market is not reacting to a headline. It is reacting to a number."
    if story.story_type == "fed_policy":
        return "The Fed story today is less about drama and more about wording."
    if story.story_type == "single_stock_filing":
        return f"{entity} moved because a formal filing changed the evidence trail."
    if story.story_type == "earnings_followthrough":
        return f"{entity} is a good reminder that a beat is not the whole story."
    return f"{entity} moved {move}% because the market found a cleaner signal than the headline."


def _bullets(story: StoryCandidate, entity: str, move: object, volume: object, source: str) -> list[str]:
    return [
        f"{entity} is tied to a {story.story_type.replace('_', ' ')} setup.",
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


def _script(hook: str, bullets: list[str], why: str, caveat: str, chart: str) -> str:
    lines = [
        hook,
        bullets[0],
        bullets[1],
        bullets[2],
        why,
        "That is why this belongs in a market-reaction slate instead of a headline recap.",
        caveat,
        f"The clean visual is simple: {chart}",
        "This is not a recommendation. It is a map of what moved, what confirmed it, and what still needs checking.",
    ]
    return "\n".join(lines)


def _thumbnail_text(story: StoryCandidate, entity: str) -> str:
    if story.story_type in {"macro_release", "fed_policy"}:
        return "The Number That Moved Rates"
    if story.story_type == "single_stock_filing":
        return "The Filing Behind The Move"
    return f"Why {entity} Moved"


def _asset_manifest(story: StoryCandidate, chart: str) -> dict[str, object]:
    return {
        "asset_bundle_id": f"bundle_{story.story_id.replace('story_', '')}",
        "story_id": story.story_id,
        "format": "vertical_1080x1920_60s",
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
