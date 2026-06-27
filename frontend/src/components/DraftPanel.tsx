import { AlertTriangle, CheckCircle2, CircleAlert, Copy, ExternalLink, FileText } from "lucide-react";
import { useEffect, useState } from "react";
import { renderPreviewUrl } from "../api";
import type { EditorialDecision, EditorialDecisionValue, QAResult, Storyboard, VideoPackage } from "../types";

interface DraftPanelProps {
  videoPackage?: VideoPackage;
  qa?: QAResult;
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
