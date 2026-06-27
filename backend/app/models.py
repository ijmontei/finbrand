from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


JsonDict = dict[str, Any]


@dataclass(slots=True)
class SourceItem:
    id: str
    source_type: str
    source_name: str
    retrieved_at: str
    published_at: str
    canonical_url: str
    title: str
    summary: str = ""
    body_text: str = ""
    language: str = "en"
    tickers: list[str] = field(default_factory=list)
    ciks: list[str] = field(default_factory=list)
    entities: list[JsonDict] = field(default_factory=list)
    themes: list[str] = field(default_factory=list)
    event_key: str | None = None
    source_authority: float = 0.5
    primary_source: bool = False
    license_notes: str = ""
    market: JsonDict = field(default_factory=dict)
    provenance: JsonDict = field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(slots=True)
class StoryCandidate:
    story_id: str
    story_date: str
    headline: str
    story_type: str
    primary_entity: JsonDict
    supporting_entities: list[str]
    cluster_item_ids: list[str]
    primary_evidence: list[JsonDict]
    metrics: JsonDict
    scores: JsonDict
    angles: list[str]
    risk_flags: list[str]
    editorial_state: str
    source_trail: list[JsonDict]

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(slots=True)
class VideoPackage:
    story_id: str
    hook: str
    summary_bullets: list[str]
    why_it_matters: str
    chart_idea: str
    caveat: str
    script_60s: str
    caption: str
    thumbnail_text: str
    risk_flags: list[str]
    asset_manifest: JsonDict
    format_key: str = ""
    format_name: str = ""
    style_variant: str = ""
    editorial_angle: str = ""

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(slots=True)
class QAGate:
    name: str
    status: str
    detail: str

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(slots=True)
class EditorialDecision:
    story_id: str
    decision: str
    editor: str
    notes: str
    decided_at: str
    qa_status: str
    story_score: float

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(slots=True)
class EditorialOverride:
    story_id: str
    override_type: str
    editor: str
    reason: str
    evidence_url: str
    created_at: str
    active: bool = True

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(slots=True)
class SourceTermsReview:
    source_name: str
    source_type: str
    review_status: str
    terms_url: str
    reviewed_by: str
    reviewed_at: str
    allowed_use: str
    restrictions: str
    expires_at: str = ""

    def to_dict(self) -> JsonDict:
        return asdict(self)
