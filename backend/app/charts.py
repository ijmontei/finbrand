from __future__ import annotations

from html import escape

from app.models import StoryCandidate


def render_signal_chart_svg(story: StoryCandidate, width: int = 1080, height: int = 1920) -> str:
    move = _as_float(story.metrics.get("price_change_pct", 0.0))
    volume = _as_float(story.metrics.get("volume_vs_20d", 1.0))
    story_score = _as_float(story.scores.get("story_score", 0.0))
    market = _as_float(story.scores.get("market_impact", 0.0))
    authority = _as_float(story.scores.get("source_authority", 0.0))
    explainability = _as_float(story.scores.get("explainability", 0.0))
    novelty = _as_float(story.scores.get("novelty", 0.0))

    series = _synthetic_series(move, volume, story_score)
    sparkline = _sparkline_points(series, 110, 740, 860, 420)
    score_bars = [
        ("Market impact", market),
        ("Source authority", authority),
        ("Explainability", explainability),
        ("Novelty", novelty),
    ]
    source = story.source_trail[0]["source_name"] if story.source_trail else "Source pending"
    direction = "up" if move >= 0 else "down"
    accent = "#56704A" if move >= 0 else "#A73234"
    title = _fit_text(story.headline, 48)
    subtitle = f"{story.primary_entity['ticker']} | {story.story_type.replace('_', ' ')} | {source}"

    bars = "\n".join(_score_bar(label, score, index) for index, (label, score) in enumerate(score_bars))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 1080 1920" role="img" aria-label="{escape(story.headline)}">
  <rect width="1080" height="1920" fill="#F4EFE4"/>
  <rect x="64" y="64" width="952" height="1792" rx="28" fill="#FAF7EF" stroke="#D8D2C3" stroke-width="2"/>
  <text x="110" y="150" fill="#6E6A61" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="30" font-weight="800" letter-spacing="3">MARKET SIGNAL STUDIO</text>
  <text x="110" y="235" fill="#1D1E20" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="56" font-weight="850">{escape(title)}</text>
  <text x="110" y="293" fill="#6E6A61" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="30" font-weight="700">{escape(subtitle)}</text>

  <rect x="110" y="365" width="860" height="520" rx="22" fill="#F7F1E6" stroke="#D8D2C3"/>
  <line x1="110" y1="740" x2="970" y2="740" stroke="#D8D2C3" stroke-width="3"/>
  <polyline points="{sparkline}" fill="none" stroke="{accent}" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="970" cy="{_last_y(series, 740, 420)}" r="15" fill="{accent}"/>
  <text x="140" y="430" fill="#6E6A61" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="28" font-weight="800">ORIGINAL SIGNAL CHART</text>
  <text x="140" y="826" fill="#6E6A61" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="24" font-weight="700">Preview uses the normalized story metrics. Verify final chart data before publishing.</text>

  <g transform="translate(110 950)">
    <rect x="0" y="0" width="410" height="188" rx="18" fill="#DDECE9"/>
    <text x="28" y="58" fill="#235653" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="28" font-weight="800">Move</text>
    <text x="28" y="132" fill="{accent}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="62" font-weight="900">{move:+.1f}%</text>
    <text x="250" y="132" fill="#6E6A61" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="28" font-weight="800">{direction}</text>

    <rect x="450" y="0" width="410" height="188" rx="18" fill="#FBEFD5"/>
    <text x="478" y="58" fill="#6D4A32" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="28" font-weight="800">Volume</text>
    <text x="478" y="132" fill="#D99028" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="62" font-weight="900">{volume:.1f}x</text>
  </g>

  <g transform="translate(110 1210)">
    <text x="0" y="0" fill="#1D1E20" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="36" font-weight="850">Score Breakdown</text>
    {bars}
  </g>

  <g transform="translate(110 1655)">
    <rect x="0" y="0" width="860" height="104" rx="18" fill="#1D1E20"/>
    <text x="34" y="44" fill="#FAF7EF" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="26" font-weight="800">Story score</text>
    <rect x="34" y="66" width="650" height="18" rx="9" fill="#6D4A32"/>
    <rect x="34" y="66" width="{round(650 * max(0, min(1, story_score)))}" height="18" rx="9" fill="#2E6F6B"/>
    <text x="720" y="75" fill="#FAF7EF" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="42" font-weight="900">{round(story_score * 100)}</text>
  </g>

  <text x="110" y="1810" fill="#6E6A61" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="24" font-weight="700">Not investment advice. Built from stored source metadata and market-reaction fields.</text>
</svg>
"""


def _as_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _score_bar(label: str, score: float, index: int) -> str:
    y = 58 + index * 92
    width = round(760 * max(0, min(1, score)))
    return f"""<g transform="translate(0 {y})">
      <text x="0" y="0" fill="#6E6A61" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="28" font-weight="780">{escape(label)}</text>
      <rect x="0" y="22" width="760" height="20" rx="10" fill="#E7DFCF"/>
      <rect x="0" y="22" width="{width}" height="20" rx="10" fill="#2E6F6B"/>
      <text x="800" y="40" fill="#1D1E20" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="28" font-weight="850">{round(score * 100)}</text>
    </g>"""


def _synthetic_series(move: float, volume: float, score: float) -> list[float]:
    baseline = 100.0
    drift = move / 8.0
    intensity = max(0.2, min(1.6, volume / 1.8))
    confidence = max(0.2, min(1.0, score))
    values = []
    for index in range(12):
        wave = ((index % 4) - 1.5) * intensity * 0.35
        step = drift * index * confidence
        values.append(baseline + step + wave)
    return values


def _sparkline_points(values: list[float], x: int, center_y: int, width: int, height: int) -> str:
    min_value = min(values)
    max_value = max(values)
    spread = max(0.1, max_value - min_value)
    step = width / (len(values) - 1)
    points = []
    for index, value in enumerate(values):
        px = x + index * step
        ratio = (value - min_value) / spread
        py = center_y + (height / 2) - (ratio * height)
        points.append(f"{px:.1f},{py:.1f}")
    return " ".join(points)


def _last_y(values: list[float], center_y: int, height: int) -> float:
    min_value = min(values)
    max_value = max(values)
    spread = max(0.1, max_value - min_value)
    ratio = (values[-1] - min_value) / spread
    return round(center_y + (height / 2) - (ratio * height), 1)


def _fit_text(value: str, max_chars: int) -> str:
    clean = " ".join(value.split())
    if len(clean) <= max_chars:
        return clean
    return clean[: max_chars - 1].rstrip() + "..."
