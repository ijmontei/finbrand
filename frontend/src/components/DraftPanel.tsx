import { AlertTriangle, CheckCircle2, CircleAlert, Copy, FileText } from "lucide-react";
import type { QAResult, Storyboard, VideoPackage } from "../types";

interface DraftPanelProps {
  videoPackage?: VideoPackage;
  qa?: QAResult;
  storyboard?: Storyboard;
  onGenerate: () => void;
  loading: boolean;
}

export function DraftPanel({ videoPackage, qa, storyboard, onGenerate, loading }: DraftPanelProps) {
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
                <strong>{storyboard.duration_sec}s</strong>
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
