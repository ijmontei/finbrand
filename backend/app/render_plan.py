from __future__ import annotations

from html import escape

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
        "editorial_format": {
            "key": package.format_key,
            "name": package.format_name,
            "style_variant": package.style_variant,
            "angle": package.editorial_angle,
        },
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


def render_preview_html(
    story: StoryCandidate,
    package: VideoPackage,
    storyboard: dict[str, object],
    qa: dict[str, object],
    chart_ref: str = "chart_signal.svg",
) -> str:
    scenes = storyboard.get("scenes", [])
    scene_markup = "\n".join(_scene_markup(scene) for scene in scenes if isinstance(scene, dict))
    source_markup = "\n".join(
        f"""<li><strong>{escape(str(item["source_name"]))}</strong><span>{escape(str(item["title"]))}</span></li>"""
        for item in story.source_trail
    )
    qa_markup = "\n".join(
        f"""<li class="{escape(str(gate["status"]))}"><strong>{escape(str(gate["name"]))}</strong><span>{escape(str(gate["detail"]))}</span></li>"""
        for gate in qa["gates"]
    )
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(story.headline)} | Market Signal Studio Preview</title>
    <style>
      :root {{
        --bg: #f4f6f8;
        --ink: #17202a;
        --muted: #637083;
        --line: #d9e0e7;
        --blue: #2563eb;
        --teal: #0f766e;
        --green: #16835a;
        --amber: #c07616;
        --red: #c93c3c;
        font-family: Inter, "Segoe UI", Arial, sans-serif;
        color: var(--ink);
        background: var(--bg);
      }}
      * {{ box-sizing: border-box; }}
      body {{ margin: 0; padding: 24px; }}
      main {{
        display: grid;
        grid-template-columns: minmax(320px, 420px) minmax(420px, 1fr);
        gap: 18px;
        max-width: 1280px;
        margin: 0 auto;
      }}
      .phone {{
        width: min(100%, 420px);
        aspect-ratio: 9 / 16;
        border-radius: 28px;
        background: #ffffff;
        border: 1px solid var(--line);
        overflow: hidden;
        box-shadow: 0 18px 48px rgba(23, 32, 42, 0.16);
      }}
      .frame {{
        display: grid;
        grid-template-rows: auto 1fr auto;
        height: 100%;
        padding: 26px;
      }}
      .brand {{ color: var(--muted); font-size: 12px; font-weight: 850; letter-spacing: 2px; text-transform: uppercase; }}
      h1 {{ margin: 14px 0 8px; font-size: 30px; line-height: 1.04; letter-spacing: 0; }}
      .meta {{ color: var(--muted); font-size: 14px; font-weight: 760; }}
      .chartWrap {{ display: grid; place-items: center; margin: 20px 0; min-height: 0; }}
      .chartWrap img {{ width: 72%; max-height: 520px; border-radius: 10px; box-shadow: 0 10px 24px rgba(23, 32, 42, 0.13); }}
      .caption {{ align-self: end; padding: 12px; border-radius: 10px; background: #17202a; color: #ffffff; font-weight: 760; line-height: 1.28; }}
      .disclaimer {{ margin-top: 10px; color: var(--muted); font-size: 12px; font-weight: 760; }}
      .panel {{ display: grid; gap: 14px; }}
      section {{ border: 1px solid var(--line); border-radius: 10px; background: #ffffff; padding: 16px; }}
      h2 {{ margin: 0 0 12px; font-size: 18px; }}
      .script {{ white-space: pre-wrap; line-height: 1.45; color: #202a38; }}
      .scenes {{ display: grid; gap: 10px; }}
      .scene {{ display: grid; grid-template-columns: 72px 1fr; gap: 10px; padding: 10px; border-radius: 8px; background: #f9fbfc; }}
      .scene time {{ color: var(--blue); font-weight: 850; }}
      .scene strong, .scene span {{ display: block; }}
      .scene span {{ margin-top: 3px; color: var(--muted); font-size: 14px; line-height: 1.35; }}
      ul {{ margin: 0; padding: 0; list-style: none; display: grid; gap: 8px; }}
      li {{ padding: 10px; border-radius: 8px; background: #f9fbfc; }}
      li strong, li span {{ display: block; }}
      li span {{ margin-top: 3px; color: var(--muted); font-size: 14px; }}
      li.pass {{ border-left: 4px solid var(--green); }}
      li.warn {{ border-left: 4px solid var(--amber); }}
      li.block {{ border-left: 4px solid var(--red); }}
      @media (max-width: 880px) {{ main {{ grid-template-columns: 1fr; }} .phone {{ margin: 0 auto; }} }}
    </style>
  </head>
  <body>
    <main>
      <article class="phone" aria-label="Vertical video preview">
        <div class="frame">
          <div>
            <div class="brand">Market Signal Studio</div>
            <h1>{escape(story.headline)}</h1>
            <div class="meta">{escape(str(story.primary_entity["ticker"]))} | {escape(story.story_type.replace("_", " "))}</div>
          </div>
          <div class="chartWrap"><img src="{escape(chart_ref)}" alt="Generated signal chart"></div>
          <div>
            <div class="caption">{escape(package.hook)}</div>
            <div class="disclaimer">Not investment advice. Verify final data and source rights before publishing.</div>
          </div>
        </div>
      </article>
      <div class="panel">
        <section>
          <h2>Storyboard</h2>
          <div class="scenes">{scene_markup}</div>
        </section>
        <section>
          <h2>Script</h2>
          <div class="script">{escape(package.script_60s)}</div>
        </section>
        <section>
          <h2>Source Trail</h2>
          <ul>{source_markup}</ul>
        </section>
        <section>
          <h2>QA Gates</h2>
          <ul>{qa_markup}</ul>
        </section>
      </div>
    </main>
  </body>
</html>
"""


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


def _scene_markup(scene: dict[str, object]) -> str:
    return f"""<div class="scene">
      <time>{escape(str(scene["start_sec"]))}-{escape(str(scene["end_sec"]))}s</time>
      <div><strong>{escape(str(scene["title"]))}</strong><span>{escape(str(scene["text_overlay"]))}</span></div>
    </div>"""


def _timestamp(seconds: float) -> str:
    total_ms = round(seconds * 1000)
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"
