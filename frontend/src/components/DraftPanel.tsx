import { AlertTriangle, CheckCircle2, CircleAlert, Copy, ExternalLink, FileText } from "lucide-react";
import { useEffect, useState } from "react";
import { renderPreviewUrl } from "../api";
import type {
  ClaimChecklist,
  EditorialDecision,
  EditorialDecisionValue,
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
  storyboard?: Storyboard;
  decision?: EditorialDecision;
  storyId?: string;
  onDecision: (decision: Exclude<EditorialDecisionValue, "pending">, notes: string) => void;
  onGenerate: () => void;
  loading: boolean;
}

export function DraftPanel({
  videoPackage,
  qa,
  claims,
  rights,
  platform,
  storyboard,
  decision,
  storyId,
  onDecision,
  onGenerate,
  loading
}: DraftPanelProps) {
  const [notes, setNotes] = useState("");

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
                <span>{rights.summary.provider_review} provider review</span>
              </div>
              <div className="rightsList">
                {rights.sources.map((source) => (
                  <div className={`rightsItem ${source.risk_level}`} key={source.source_id}>
                    <strong>{source.source_name}</strong>
                    <span>{source.review_action}</span>
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
              <button onClick={() => onDecision("approve", notes)} className="decisionButton approve">Approve</button>
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
