export type ScoreKey =
  | "market_impact"
  | "novelty"
  | "source_authority"
  | "timeliness"
  | "corroboration"
  | "explainability"
  | "buzz_proxy"
  | "story_score";

export interface SourceTrailItem {
  id: string;
  source_name: string;
  source_type: string;
  title: string;
  url: string;
  primary_source: boolean;
  license_notes: string;
}

export interface Story {
  story_id: string;
  story_date: string;
  headline: string;
  story_type: string;
  primary_entity: {
    ticker: string;
    name: string;
  };
  supporting_entities: string[];
  cluster_item_ids: string[];
  primary_evidence: Array<Record<string, string>>;
  metrics: Record<string, number | boolean>;
  scores: Record<ScoreKey, number>;
  angles: string[];
  risk_flags: string[];
  editorial_state: "draft_ready" | "editor_review" | "archive";
  source_trail: SourceTrailItem[];
}

export interface VideoPackage {
  story_id: string;
  hook: string;
  summary_bullets: string[];
  why_it_matters: string;
  chart_idea: string;
  caveat: string;
  script_60s: string;
  caption: string;
  thumbnail_text: string;
  risk_flags: string[];
  asset_manifest: Record<string, unknown>;
}

export interface QAGate {
  name: string;
  status: "pass" | "warn" | "block";
  detail: string;
}

export interface QAResult {
  story_id: string;
  status: "ready" | "needs_review" | "blocked";
  gates: QAGate[];
}

export interface StoryboardScene {
  id: string;
  title: string;
  start_sec: number;
  end_sec: number;
  duration_sec: number;
  text_overlay: string;
  narration: string;
  asset_ref?: string | null;
  editor_note: string;
}

export interface Storyboard {
  story_id: string;
  format: string;
  duration_sec: number;
  safe_zones: Record<string, number>;
  assets: Record<string, string>;
  scenes: StoryboardScene[];
}

export type EditorialDecisionValue = "pending" | "approve" | "hold" | "revise" | "archive";

export interface EditorialDecision {
  story_id: string;
  decision: EditorialDecisionValue;
  editor: string;
  notes: string;
  decided_at: string | null;
  qa_status: QAResult["status"];
  story_score: number;
}

export interface ClaimItem {
  claim_id: string;
  text: string;
  source_refs: string[];
  verification_status: "ready" | "source_backed" | "editor_verify" | "needs_source" | "needs_primary_source";
  editor_note: string;
}

export interface ClaimChecklist {
  story_id: string;
  status: "ready" | "needs_review" | "blocked";
  claims: ClaimItem[];
}

export interface RightsSource {
  source_id: string;
  source_name: string;
  source_type: string;
  title: string;
  url: string;
  primary_source: boolean;
  license_notes: string;
  posture: "official" | "first_party" | "provider_review" | "missing_notes" | "unknown";
  risk_level: "low" | "medium" | "high";
  allowed_use: string;
  review_action: string;
}

export interface RightsReport {
  story_id: string;
  status: "ready" | "needs_review" | "blocked";
  summary: {
    source_count: number;
    official_or_first_party: number;
    provider_review: number;
    missing_license_notes: number;
  };
  sources: RightsSource[];
  required_actions: string[];
  publish_rule: string;
}
