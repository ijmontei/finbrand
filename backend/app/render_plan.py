from __future__ import annotations

from app.models import StoryCandidate, VideoPackage


def build_storyboard(story: StoryCandidate, package: VideoPackage) -> dict[str, object]:
    scenes = [
        _scene(
            "hook",
            "Hook",
            0,
            6,
            package.hook,
            package.hook,
            "Kinetic text over branded market signal background.",
        ),
        _scene(
            "event",
            "What Happened",
            6,
            18,
            package.summary_bullets[0],
            "\n".join(package.summary_bullets),
            "Use source badges and one-line factual setup.",
        ),
        _scene(
            "signal",
            "Market Signal",
            18,
            34,
            f"{story.primary_entity['ticker']} move: {story.metrics.get('price_change_pct', 0)}%",
            package.chart_idea,
            "Show chart_signal.svg with move, volume, and score bars.",
            asset_ref="chart_signal.svg",
        ),
        _scene(
            "meaning",
            "Why It Matters",
            34,
            48,
            package.why_it_matters,
            package.why_it_matters,
            "Keep text inside vertical safe zone and avoid price-target framing.",
        ),
        _scene(
            "caveat",
            "Caveat",
            48,
            56,
            package.caveat,
            package.caveat,
            "Visually mark uncertainty so the video does not overclaim causality.",
        ),
        _scene(
            "disclaimer",
            "Close",
            56,
            60,
            "Not investment advice.",
            "This is not a recommendation. It is a map of what moved, what confirmed it, and what still needs checking.",
            "End with source-aware disclaimer and optional newsletter CTA.",
        ),
    ]
    return {
        "story_id": story.story_id,
        "format": "vertical_1080x1920_60s",
        "duration_sec": 60,
        "safe_zones": {
            "top_px": 180,
            "bottom_px": 260,
            "left_px": 90,
            "right_px": 90,
        },
        "assets": {
            "chart": "chart_signal.svg",
            "captions": "captions.srt",
        },
        "scenes": scenes,
    }


def generate_srt(package: VideoPackage, target_duration_sec: int = 60) -> str:
    lines = [line.strip() for line in package.script_60s.splitlines() if line.strip()]
    word_counts = [max(1, len(line.split())) for line in lines]
    total_words = sum(word_counts) or 1
    cursor = 0.0
    cues: list[str] = []
    for index, (line, words) in enumerate(zip(lines, word_counts, strict=True), start=1):
        duration = target_duration_sec * (words / total_words)
        end = target_duration_sec if index == len(lines) else cursor + duration
        cues.append(f"{index}\n{_timestamp(cursor)} --> {_timestamp(end)}\n{line}\n")
        cursor = end
    return "\n".join(cues).strip() + "\n"


def _scene(
    scene_id: str,
    title: str,
    start_sec: int,
    end_sec: int,
    text_overlay: str,
    narration: str,
    editor_note: str,
    asset_ref: str | None = None,
) -> dict[str, object]:
    return {
        "id": scene_id,
        "title": title,
        "start_sec": start_sec,
        "end_sec": end_sec,
        "duration_sec": end_sec - start_sec,
        "text_overlay": text_overlay,
        "narration": narration,
        "asset_ref": asset_ref,
        "editor_note": editor_note,
    }


def _timestamp(seconds: float) -> str:
    total_ms = round(seconds * 1000)
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

