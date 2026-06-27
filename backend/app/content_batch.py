from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone

from app.approval import build_approval_checklist
from app.claims import build_claim_checklist
from app.models import StoryCandidate, VideoPackage
from app.pipeline.compliance import run_qa
from app.pipeline.script_writer import generate_video_package
from app.platform import build_platform_readiness
from app.publish_packet import build_publish_packet
from app.rights import build_rights_report


@dataclass(frozen=True, slots=True)
class ContentLens:
    key: str
    name: str
    editorial_job: str
    hook_frame: str
    evidence_frame: str
    chart_direction: str
    caption_tail: str


@dataclass(frozen=True, slots=True)
class PlatformPlaybook:
    key: str
    name: str
    deliverable: str
    target_length: str
    adaptation_note: str


CONTENT_LENSES = [
    ContentLens(
        key="why_it_moved",
        name="Why It Moved",
        editorial_job="Explain the trigger, the market reaction, and the evidence trail in one clean sequence.",
        hook_frame="The useful question is not that {entity} moved. It is what changed in the evidence.",
        evidence_frame="Anchor the story in the strongest source first, then explain the reaction.",
        chart_direction="Lead with the move, then annotate the source timestamp.",
        caption_tail="A source-backed read on what moved, what confirmed it, and what still needs checking.",
    ),
    ContentLens(
        key="data_everyone_missed",
        name="The Data Everyone Missed",
        editorial_job="Separate the obvious headline from the data point that makes the story explainable.",
        hook_frame="The headline is visible. The data signal behind {entity} is the part worth slowing down.",
        evidence_frame="Call out the market signal before repeating any source summary.",
        chart_direction="Show the price or rate move beside the confirming data point.",
        caption_tail="The market reaction makes more sense when the missing data point is on screen.",
    ),
    ContentLens(
        key="market_misread",
        name="The Market Misread",
        editorial_job="Challenge the first-read narrative without turning the draft into a prediction.",
        hook_frame="{entity} may be a good example of the market reacting faster than the facts are settling.",
        evidence_frame="Compare the first interpretation with what the source trail actually supports.",
        chart_direction="Use a split-screen: first take on one side, source-backed signal on the other.",
        caption_tail="A check on the easy market narrative, not a buy or sell call.",
    ),
    ContentLens(
        key="three_signals",
        name="Three Signals",
        editorial_job="Turn the story into three fast signals: source, market reaction, and caveat.",
        hook_frame="Three signals explain why {entity} belongs on the market-reaction slate.",
        evidence_frame="Number the source trail, move size, and uncertainty note.",
        chart_direction="Use three labeled beats: source, reaction, watch-next.",
        caption_tail="Three signals, one chart idea, and one caveat before anyone overreads the move.",
    ),
    ContentLens(
        key="chart_first",
        name="Chart First",
        editorial_job="Make the owned visual the lead so the output is more than a headline recap.",
        hook_frame="Start with the chart: {entity} only becomes a real story if the move has evidence behind it.",
        evidence_frame="Let the source citation explain the chart annotation, not the other way around.",
        chart_direction="Open on a clean annotated chart with one number and one source label.",
        caption_tail="The chart is the point: one signal, one source trail, one caveat.",
    ),
    ContentLens(
        key="source_trail",
        name="Source Trail",
        editorial_job="Show why the story is publishable or why it still needs review.",
        hook_frame="Before turning {entity} into content, check what the source trail actually proves.",
        evidence_frame="Name the primary or first-party source and flag any provider-rights review.",
        chart_direction="Pair the source citation with a simple reaction chart.",
        caption_tail="A transparent source trail keeps this from becoming recycled market noise.",
    ),
    ContentLens(
        key="risk_caveat",
        name="The Caveat",
        editorial_job="Lead with uncertainty so the draft feels like judgment, not hype.",
        hook_frame="The important part of the {entity} move is the caveat most recaps skip.",
        evidence_frame="Explain what is known, what is not known, and what would confirm the read.",
        chart_direction="Mark the chart with a watch-next label instead of a prediction.",
        caption_tail="The caveat is not decoration. It is the reason this stays analytical.",
    ),
    ContentLens(
        key="before_open",
        name="Before The Open",
        editorial_job="Frame the story as a pre-market watch item with explicit uncertainty.",
        hook_frame="Before the open, {entity} is worth watching because the source trail changed the setup.",
        evidence_frame="Keep it forward-looking in an observational way, without advice language.",
        chart_direction="Use a pre-market checklist beside the source-backed signal.",
        caption_tail="A pre-market watch item, not a recommendation.",
    ),
    ContentLens(
        key="after_close",
        name="After The Close",
        editorial_job="Summarize the finished reaction and what evidence mattered by the close.",
        hook_frame="After the close, the {entity} move is easier to judge against the source trail.",
        evidence_frame="Explain whether the reaction matched the evidence or got ahead of it.",
        chart_direction="Show open-to-close reaction with one source annotation.",
        caption_tail="An after-close explanation of what the market priced and what still needs review.",
    ),
    ContentLens(
        key="newsletter_teaser",
        name="Newsletter Teaser",
        editorial_job="Convert the story into an owned-audience teaser that points back to the research packet.",
        hook_frame="{entity} is the kind of market move that deserves a source-backed explanation, not a headline skim.",
        evidence_frame="Write it as a concise owned-audience note with citations preserved.",
        chart_direction="Use the chart idea as the reason to click into the full brief.",
        caption_tail="The full value is the source-backed chart and caveat, not the headline.",
    ),
]


PLATFORM_PLAYBOOKS = [
    PlatformPlaybook(
        key="youtube_shorts",
        name="YouTube Shorts",
        deliverable="60-second vertical video script",
        target_length="120-155 spoken words",
        adaptation_note="Title and first line should make the analytical payoff clear without sounding like a generic headline recap.",
    ),
    PlatformPlaybook(
        key="instagram_reels",
        name="Instagram Reels",
        deliverable="vertical video caption and cover copy",
        target_length="short caption plus 60-second script",
        adaptation_note="Keep the cover text centered and make the caption transformation obvious.",
    ),
    PlatformPlaybook(
        key="tiktok",
        name="TikTok",
        deliverable="fast-hook vertical video script",
        target_length="45-60 second script",
        adaptation_note="Lead with the market question, then move quickly to the chart and caveat.",
    ),
    PlatformPlaybook(
        key="newsletter",
        name="Newsletter",
        deliverable="owned-audience market note",
        target_length="120-180 written words",
        adaptation_note="Preserve source citations and make the chart-to-watch the reason to read.",
    ),
    PlatformPlaybook(
        key="linkedin",
        name="LinkedIn",
        deliverable="source-backed market commentary post",
        target_length="100-160 written words",
        adaptation_note="Use a more measured voice and foreground the business or macro implication.",
    ),
]


def build_content_batch(
    stories: list[StoryCandidate],
    count: int = 50,
    decisions_by_story: dict[str, dict[str, object]] | None = None,
    overrides_by_story: dict[str, list[dict[str, object]]] | None = None,
    source_terms: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    if count < 1:
        raise ValueError("count must be at least 1")
    ranked_stories = sorted(
        stories,
        key=lambda story: (-float(story.scores.get("story_score", 0)), story.story_id),
    )
    if not ranked_stories:
        raise ValueError("at least one story is required to build a content batch")

    decision_map = decisions_by_story or {}
    override_map = overrides_by_story or {}
    contexts = {
        story.story_id: _story_context(
            story,
            decision_map.get(story.story_id),
            override_map.get(story.story_id, []),
            source_terms,
        )
        for story in ranked_stories
    }
    pieces = []
    for index in range(count):
        story = ranked_stories[index % len(ranked_stories)]
        lens = CONTENT_LENSES[(index // len(PLATFORM_PLAYBOOKS)) % len(CONTENT_LENSES)]
        platform = PLATFORM_PLAYBOOKS[index % len(PLATFORM_PLAYBOOKS)]
        pieces.append(_content_piece(index + 1, story, contexts[story.story_id], lens, platform))

    return {
        "batch_id": f"launch_batch_{count}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "requested_count": count,
        "count": len(pieces),
        "publish_mode": "manual_only",
        "auto_post_allowed": False,
        "batch_rule": "This creates draft content pieces only. Every piece requires human review and manual publishing.",
        "source_policy": "Use source citations and derived commentary; do not republish article text or raw market-data feeds without reviewed rights.",
        "status_summary": dict(Counter(str(piece["publish_status"]) for piece in pieces)),
        "platform_mix": dict(Counter(str(piece["platform"]["key"]) for piece in pieces)),
        "lens_mix": dict(Counter(str(piece["content_lens"]["key"]) for piece in pieces)),
        "pieces": pieces,
    }


def render_content_batch_markdown(batch: dict[str, object]) -> str:
    pieces = batch["pieces"]
    lines = [
        f"# Content Batch: {batch['count']} Draft Pieces",
        "",
        f"Mode: {batch['publish_mode']}",
        f"Auto-post allowed: {batch['auto_post_allowed']}",
        "",
        str(batch["batch_rule"]),
        "",
        "## Status Summary",
        "",
    ]
    for status, total in batch["status_summary"].items():
        lines.append(f"- {status}: {total}")
    lines.extend(["", "## Pieces", ""])
    for piece in pieces:
        lines.extend(
            [
                f"### {piece['sequence']:03d}. {piece['title']}",
                "",
                f"- ID: `{piece['content_id']}`",
                f"- Story: {piece['headline']}",
                f"- Platform: {piece['platform']['name']} ({piece['platform']['deliverable']})",
                f"- Lens: {piece['content_lens']['name']}",
                f"- Publish status: {piece['publish_status']}",
                f"- Manual publish required: {piece['manual_publish_required']}",
                "",
                "**Hook**",
                "",
                str(piece["hook"]),
                "",
                "**Draft**",
                "",
                str(piece["script_or_body"]),
                "",
                "**Sources**",
                "",
            ]
        )
        for source in piece["source_refs"]:
            lines.append(f"- {source['source_name']}: {source['title']} ({source['url']})")
        lines.extend(["", "**Review Snapshot**", ""])
        review = piece["review"]
        lines.extend(
            [
                f"- QA: {review['qa_status']}",
                f"- Claims: {review['claims_status']}",
                f"- Rights: {review['rights_status']}",
                f"- Platform: {review['platform_status']}",
                f"- Approval: {review['approval_status']}",
                "",
            ]
        )
    return "\n".join(lines)


def render_content_piece_markdown(piece: dict[str, object]) -> str:
    source_lines = "\n".join(
        f"- {source['source_name']}: {source['title']} ({source['url']})" for source in piece["source_refs"]
    )
    blockers = "\n".join(f"- {item}" for item in piece["blockers"]) or "- None"
    warnings = "\n".join(f"- {item}" for item in piece["warnings"]) or "- None"
    return f"""# {piece["title"]}

ID: `{piece["content_id"]}`
Story: {piece["headline"]}
Platform: {piece["platform"]["name"]}
Deliverable: {piece["platform"]["deliverable"]}
Lens: {piece["content_lens"]["name"]}
Publish status: {piece["publish_status"]}
Auto-post allowed: {piece["auto_post_allowed"]}

## Hook

{piece["hook"]}

## Draft

{piece["script_or_body"]}

## Caption

{piece["caption"]}

## Thumbnail / Cover

{piece["thumbnail_text"]}

## Chart Direction

{piece["chart_idea"]}

## Sources

{source_lines}

## Blockers

{blockers}

## Warnings

{warnings}

## Required Next Step

{piece["required_next_step"]}
"""


def _story_context(
    story: StoryCandidate,
    decision: dict[str, object] | None,
    editorial_overrides: list[dict[str, object]],
    source_terms: list[dict[str, object]] | None,
) -> dict[str, object]:
    package = generate_video_package(story)
    qa = run_qa(story, package, editorial_overrides=editorial_overrides, source_terms=source_terms)
    claims = build_claim_checklist(story, package, editorial_overrides=editorial_overrides)
    rights = build_rights_report(story, source_terms=source_terms)
    platform = build_platform_readiness(story, package)
    approval = build_approval_checklist(
        story,
        package,
        editorial_overrides=editorial_overrides,
        source_terms=source_terms,
    )
    editorial_decision = decision or _pending_decision(story, qa)
    publish_packet = build_publish_packet(story, package, qa, claims, rights, platform, approval, editorial_decision)
    return {
        "package": package,
        "qa": qa,
        "claims": claims,
        "rights": rights,
        "platform": platform,
        "approval": approval,
        "decision": editorial_decision,
        "publish_packet": publish_packet,
    }


def _content_piece(
    sequence: int,
    story: StoryCandidate,
    context: dict[str, object],
    lens: ContentLens,
    platform: PlatformPlaybook,
) -> dict[str, object]:
    package = context["package"]
    if not isinstance(package, VideoPackage):
        raise TypeError("content batch context package must be a VideoPackage")
    publish_packet = context["publish_packet"]
    if not isinstance(publish_packet, dict):
        raise TypeError("content batch context publish_packet must be a dict")
    title = _title(story, package, lens, platform)
    hook = _hook(story, package, lens)
    return {
        "content_id": _content_id(sequence, story, lens, platform),
        "sequence": sequence,
        "story_id": story.story_id,
        "headline": story.headline,
        "story_type": story.story_type,
        "primary_entity": story.primary_entity,
        "platform": {
            "key": platform.key,
            "name": platform.name,
            "deliverable": platform.deliverable,
            "target_length": platform.target_length,
            "adaptation_note": platform.adaptation_note,
        },
        "content_lens": {
            "key": lens.key,
            "name": lens.name,
            "editorial_job": lens.editorial_job,
        },
        "title": title,
        "hook": hook,
        "script_or_body": _draft_body(story, package, lens, platform, hook),
        "caption": _caption(story, package, lens, platform),
        "thumbnail_text": _thumbnail_text(story, package, lens),
        "chart_idea": f"{lens.chart_direction} Base chart: {package.chart_idea}",
        "source_refs": _source_refs(story),
        "review": {
            "qa_status": context["qa"]["status"],
            "claims_status": context["claims"]["status"],
            "rights_status": context["rights"]["status"],
            "platform_status": context["platform"]["status"],
            "approval_status": context["approval"]["status"],
            "decision": context["decision"],
        },
        "publish_status": publish_packet["status"],
        "manual_publish_required": True,
        "auto_post_allowed": False,
        "blockers": publish_packet["blockers"],
        "warnings": publish_packet["warnings"],
        "required_next_step": _required_next_step(publish_packet),
        "disclaimer": "This is not personalized investment advice.",
    }


def _draft_body(
    story: StoryCandidate,
    package: VideoPackage,
    lens: ContentLens,
    platform: PlatformPlaybook,
    hook: str,
) -> str:
    source_name = _source_name(story)
    market_line = _market_line(story)
    lines = [
        hook,
        package.summary_bullets[0],
        f"The signal: {market_line}",
        f"The evidence frame: {lens.evidence_frame}",
        f"Primary source to cite: {source_name}.",
        package.why_it_matters,
        f"The caveat: {package.caveat}",
        f"Visual direction: {lens.chart_direction} {package.chart_idea}",
        "This is not a recommendation. It is a source-backed explanation of what moved, what confirmed it, and what still needs checking.",
    ]
    if platform.key == "newsletter":
        lines.insert(1, f"Newsletter angle: {lens.editorial_job}")
    if platform.key == "linkedin":
        lines.insert(1, "Business context: keep the voice measured, cite the source trail, and avoid trade instructions.")
    return "\n".join(lines)


def _title(story: StoryCandidate, package: VideoPackage, lens: ContentLens, platform: PlatformPlaybook) -> str:
    entity = story.primary_entity.get("name", "Market")
    if platform.key == "newsletter":
        return f"{lens.name}: {entity} in the daily brief"
    if platform.key == "linkedin":
        return f"What {entity} shows about today's market reaction"
    return f"{lens.name}: {package.thumbnail_text}"


def _hook(story: StoryCandidate, package: VideoPackage, lens: ContentLens) -> str:
    entity = story.primary_entity.get("name", "this market move")
    return f"{lens.hook_frame.format(entity=entity)} {package.hook}"


def _caption(story: StoryCandidate, package: VideoPackage, lens: ContentLens, platform: PlatformPlaybook) -> str:
    ticker = story.primary_entity.get("ticker", "MARKET")
    if platform.key == "newsletter":
        return f"{story.headline} {lens.caption_tail} Source trail preserved. Not personalized investment advice."
    if platform.key == "linkedin":
        return f"{lens.caption_tail} Source trail: {_source_name(story)}. Not personalized investment advice."
    return f"{package.caption} {lens.caption_tail} #{ticker} #markets #finance"


def _thumbnail_text(story: StoryCandidate, package: VideoPackage, lens: ContentLens) -> str:
    ticker = story.primary_entity.get("ticker", "")
    prefix = lens.name.replace("The ", "")
    if ticker:
        return f"{prefix}: {ticker}"
    return f"{prefix}: {package.thumbnail_text}"


def _source_refs(story: StoryCandidate) -> list[dict[str, object]]:
    return [
        {
            "source_name": item["source_name"],
            "source_type": item["source_type"],
            "title": item["title"],
            "url": item["url"],
            "primary_source": item["primary_source"],
            "license_notes": item["license_notes"],
        }
        for item in story.source_trail[:3]
    ]


def _source_name(story: StoryCandidate) -> str:
    if story.source_trail:
        return str(story.source_trail[0]["source_name"])
    return "source review pending"


def _market_line(story: StoryCandidate) -> str:
    price_move = story.metrics.get("price_change_pct")
    volume = story.metrics.get("volume_vs_20d")
    if price_move is not None and volume is not None:
        return f"{price_move}% price action with volume near {volume} times normal."
    if price_move is not None:
        return f"{price_move}% price action."
    return "The market signal needs editor verification before publication."


def _content_id(sequence: int, story: StoryCandidate, lens: ContentLens, platform: PlatformPlaybook) -> str:
    story_suffix = story.story_id.replace("story_", "")
    return f"piece_{sequence:03d}_{story_suffix}_{lens.key}_{platform.key}"


def _pending_decision(story: StoryCandidate, qa: dict[str, object]) -> dict[str, object]:
    return {
        "story_id": story.story_id,
        "decision": "pending",
        "editor": "",
        "notes": "",
        "decided_at": None,
        "qa_status": qa["status"],
        "story_score": story.scores["story_score"],
    }


def _required_next_step(publish_packet: dict[str, object]) -> str:
    if publish_packet["status"] == "ready_manual_publish":
        return "Run final human upload review, publish manually, then archive the final URL and performance metrics."
    return "Clear blockers, record an approved editor decision with notes when required, then regenerate the publish packet."
