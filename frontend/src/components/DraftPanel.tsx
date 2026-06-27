import { AlertTriangle, CheckCircle2, CircleAlert, Copy, ExternalLink, FileText } from "lucide-react";
import { useEffect, useState } from "react";
import { renderPreviewUrl } from "../api";
import type {
  ApprovalChecklist,
  ClaimChecklist,
  EditorialDecision,
  EditorialDecisionValue,
  EditorialOverride,
  PlatformReadiness,
  QAResult,
  RightsReport,
  Storyboard,
  VideoPackage
} from "../types";

interface DraftPanelProps {
  videoPackage?: VideoPackage;
  qa?: QAResult;
  claims?: ClaimChecklist;
  rights?: RightsReport;
  platform?: PlatformReadiness;
  approval?: ApprovalChecklist;
  storyboard?: Storyboard;
  decision?: EditorialDecision;
  overrides?: EditorialOverride[];
  storyId?: string;
  onDecision: (decision: Exclude<EditorialDecisionValue, "pending">, notes: string) => void;
  onOverride: (reason: string, evidenceUrl: string) => void;
  onGenerate: () => void;
  loading: boolean;
}

export function DraftPanel({
  videoPackage,
  qa,
  claims,
  rights,
  platform,
  approval,
  storyboard,
  decision,
  overrides = [],
  storyId,
  onDecision,
  onOverride,
  onGenerate,
  loading
}: DraftPanelProps) {
  const [notes, setNotes] = useState("");
  const [overrideReason, setOverrideReason] = useState("");
  const [overrideEvidenceUrl, setOverrideEvidenceUrl] = useState("");
  const approveDisabled = Boolean(
    approval && (!approval.can_approve || (approval.notes_required && !notes.trim()))
  );
  const overrideDisabled = !storyId || overrideReason.trim().length < 20 || overrideEvidenceUrl.trim().length < 8;

  useEffect(() => {
    setNotes(decision?.notes ?? "");
  }, [decision?.story_id, decision?.notes]);

  return (
    <aside className="draftPanel">
      <div className="panelHeader">
        <div>
          <p className="eyebrow">Output</p>
          <h2>Draft Package</h2>
        </div>
        <button className="iconButton primary" onClick={onGenerate} title="Generate draft package" aria-label="Generate draft package">
          <FileText size={18} />
          <span>{loading ? "Working" : "Draft"}</span>
        </button>
      </div>

      {videoPackage ? (
        <>
          <section className="formatBox">
            <div>
              <span>{videoPackage.format_name || "Editorial format"}</span>
              <strong>{videoPackage.style_variant || "source-backed explainer"}</strong>
            </div>
            <p>{videoPackage.editorial_angle || "Explain the market reaction with source-backed context."}</p>
          </section>

          <section className="draftBlock">
            <p className="eyebrow">Hook</p>
            <h3>{videoPackage.hook}</h3>
          </section>

          <section className="scriptBox">
            <div className="scriptHeader">
              <span>60s Script</span>
              <button
                className="iconButton ghost"
                title="Copy script"
                aria-label="Copy script"
                onClick={() => navigator.clipboard.writeText(videoPackage.script_60s)}
              >
                <Copy size={16} />
              </button>
            </div>
            <pre>{videoPackage.script_60s}</pre>
          </section>

          {storyboard ? (
            <section className="storyboardBox">
              <div className="scriptHeader">
                <span>Storyboard</span>
                <div className="headerTools">
                  {storyId ? (
                    <a
                      className="miniLink"
                      href={renderPreviewUrl(storyId)}
                      target="_blank"
                      rel="noreferrer"
                      title="Open render preview"
                      aria-label="Open render preview"
                    >
                      <ExternalLink size={15} />
                    </a>
                  ) : null}
                  <strong>{storyboard.duration_sec}s</strong>
                </div>
              </div>
              <div className="sceneList">
                {storyboard.scenes.map((scene) => (
                  <div className="sceneItem" key={scene.id}>
                    <time>
                      {scene.start_sec}-{scene.end_sec}s
                    </time>
                    <div>
                      <strong>{scene.title}</strong>
                      <span>{scene.text_overlay}</span>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          ) : null}

          <section className="qaBox">
            <div className="qaStatus">
              {qa?.status === "ready" ? <CheckCircle2 size={20} /> : <CircleAlert size={20} />}
              <strong>{qa?.status?.replace("_", " ") ?? "QA pending"}</strong>
            </div>
            <div className="qaGates">
              {qa?.gates.map((gate) => (
                <div className={`qaGate ${gate.status}`} key={gate.name}>
                  {gate.status === "pass" ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
                  <div>
                    <strong>{gate.name}</strong>
                    <span>{gate.detail}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {claims ? (
            <section className="claimsBox">
              <div className="scriptHeader">
                <span>Claims</span>
                <strong>{claims.status.replace("_", " ")}</strong>
              </div>
              <div className="claimList">
                {claims.claims.map((claim) => (
                  <div className={`claimItem ${claim.verification_status}`} key={claim.claim_id}>
                    <strong>{claim.verification_status.replaceAll("_", " ")}</strong>
                    <span>{claim.text}</span>
                    <small>{claim.editor_note}</small>
                  </div>
                ))}
              </div>
            </section>
          ) : null}

          {rights ? (
            <section className="rightsBox">
              <div className="scriptHeader">
                <span>Rights</span>
                <strong>{rights.status.replace("_", " ")}</strong>
              </div>
              <div className="rightsSummary">
                <span>{rights.summary.source_count} sources</span>
                <span>{rights.summary.official_or_first_party} official/first-party</span>
                <span>{rights.summary.licensed} licensed</span>
                <span>{rights.summary.provider_review} provider review</span>
              </div>
              <div className="rightsList">
                {rights.sources.map((source) => (
                  <div className={`rightsItem ${source.risk_level}`} key={source.source_id}>
                    <strong>{source.source_name}</strong>
                    <span>{source.review_action}</span>
                    <small>Terms: {source.terms_status}</small>
                    <small>{source.allowed_use}</small>
                  </div>
                ))}
              </div>
            </section>
          ) : null}

          {platform ? (
            <section className="platformBox">
              <div className="scriptHeader">
                <span>Platform</span>
                <strong>{platform.status.replace("_", " ")}</strong>
              </div>
              <div className="platformScore">
                <div>
                  <span>Originality</span>
                  <strong>{Math.round(platform.originality_score * 100)}</strong>
                </div>
                <div>
                  <span>Risk</span>
                  <strong>{platform.risk_level}</strong>
                </div>
              </div>
              <div className="platformChecks">
                {platform.checks.map((check) => (
                  <div className={`platformCheck ${check.status}`} key={check.id}>
                    <strong>{check.name}</strong>
                    <span>{check.detail}</span>
                    {check.status === "pass" ? null : <small>{check.editorial_action}</small>}
                  </div>
                ))}
              </div>
            </section>
          ) : null}

          {approval ? (
            <section className="approvalBox">
              <div className="scriptHeader">
                <span>Approval</span>
                <strong>{approval.status.replace("_", " ")}</strong>
              </div>
              <div className="approvalSummary">
                <span>{approval.can_approve ? "Can approve" : "Blocked"}</span>
                <span>{approval.notes_required ? "Notes required" : "Notes optional"}</span>
              </div>
              <div className="approvalChecks">
                {approval.checks.map((check) => (
                  <div className={`approvalCheck ${check.status}`} key={check.id}>
                    <strong>{check.name}</strong>
                    <span>{check.detail}</span>
                  </div>
                ))}
              </div>
            </section>
          ) : null}

          <section className="overrideBox">
            <div className="scriptHeader">
              <span>Editorial Overrides</span>
              <strong>{overrides.length}</strong>
            </div>
            {overrides.length ? (
              <div className="overrideList">
                {overrides.map((override) => (
                  <div className="overrideItem" key={`${override.override_type}-${override.created_at}`}>
                    <strong>{override.override_type.replace("_", " ")}</strong>
                    <span>{override.reason}</span>
                    <small>
                      {override.editor} - {new Date(override.created_at).toLocaleString()}
                    </small>
                  </div>
                ))}
              </div>
            ) : null}
            <div className="overrideForm">
              <textarea
                value={overrideReason}
                onChange={(event) => setOverrideReason(event.target.value)}
                placeholder="Reason for primary-source override."
                aria-label="Primary-source override reason"
              />
              <input
                value={overrideEvidenceUrl}
                onChange={(event) => setOverrideEvidenceUrl(event.target.value)}
                placeholder="https://... or internal://..."
                aria-label="Primary-source override evidence URL"
              />
              <button
                className="decisionButton revise"
                disabled={overrideDisabled}
                onClick={() => {
                  onOverride(overrideReason, overrideEvidenceUrl);
                  setOverrideReason("");
                  setOverrideEvidenceUrl("");
                }}
                title="Record primary-source override"
              >
                Record Override
              </button>
            </div>
          </section>

          <section className="decisionBox">
            <div className="scriptHeader">
              <span>Editor Decision</span>
              <strong>{decision?.decision ?? "pending"}</strong>
            </div>
            <textarea
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              placeholder="Add source, framing, rights, or revision notes."
              aria-label="Editorial decision notes"
            />
            <div className="decisionActions">
              <button
                onClick={() => onDecision("approve", notes)}
                className="decisionButton approve"
                disabled={approveDisabled}
                title={approveDisabled ? "Clear blockers or add approval notes first" : "Approve package"}
              >
                Approve
              </button>
              <button onClick={() => onDecision("hold", notes)} className="decisionButton hold">Hold</button>
              <button onClick={() => onDecision("revise", notes)} className="decisionButton revise">Revise</button>
              <button onClick={() => onDecision("archive", notes)} className="decisionButton archive">Archive</button>
            </div>
            {decision?.decided_at ? <small>Saved {new Date(decision.decided_at).toLocaleString()}</small> : null}
          </section>
        </>
      ) : (
        <div className="emptyState">
          <FileText size={28} />
          <strong>No draft selected</strong>
        </div>
      )}
    </aside>
  );
}
