import { RefreshCw, ShieldCheck, Wand2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  fetchApproval,
  fetchClaims,
  fetchDecision,
  fetchOverrides,
  fetchPlatformReadiness,
  fetchPublishPacket,
  fetchQA,
  fetchRights,
  fetchStoryboard,
  fetchStories,
  generatePackage,
  recordPrimarySourceOverride,
  recordDecision,
  refreshStories
} from "./api";
import { DraftPanel } from "./components/DraftPanel";
import { ScoreMeter } from "./components/ScoreMeter";
import { SignalChart } from "./components/SignalChart";
import { SourceTrail } from "./components/SourceTrail";
import { StoryQueue } from "./components/StoryQueue";
import type {
  ClaimChecklist,
  ApprovalChecklist,
  EditorialDecision,
  EditorialDecisionValue,
  EditorialOverride,
  PlatformReadiness,
  PublishPacket,
  QAResult,
  RightsReport,
  Story,
  Storyboard,
  VideoPackage
} from "./types";

const scoreLabels = [
  ["market_impact", "Market impact"],
  ["novelty", "Novelty"],
  ["source_authority", "Authority"],
  ["timeliness", "Timeliness"],
  ["corroboration", "Corroboration"],
  ["explainability", "Explainability"]
] as const;

export default function App() {
  const [stories, setStories] = useState<Story[]>([]);
  const [selectedId, setSelectedId] = useState<string>();
  const [videoPackage, setVideoPackage] = useState<VideoPackage>();
  const [qa, setQa] = useState<QAResult>();
  const [claims, setClaims] = useState<ClaimChecklist>();
  const [rights, setRights] = useState<RightsReport>();
  const [platform, setPlatform] = useState<PlatformReadiness>();
  const [approval, setApproval] = useState<ApprovalChecklist>();
  const [publishPacket, setPublishPacket] = useState<PublishPacket>();
  const [storyboard, setStoryboard] = useState<Storyboard>();
  const [decision, setDecision] = useState<EditorialDecision>();
  const [overrides, setOverrides] = useState<EditorialOverride[]>([]);
  const [loading, setLoading] = useState(true);
  const [drafting, setDrafting] = useState(false);
  const [error, setError] = useState<string>();

  useEffect(() => {
    void loadStories();
  }, []);

  const selectedStory = useMemo(
    () => stories.find((story) => story.story_id === selectedId) ?? stories[0],
    [stories, selectedId]
  );

  useEffect(() => {
    if (selectedStory) {
      void buildDraft(selectedStory.story_id);
    }
  }, [selectedStory?.story_id]);

  async function loadStories() {
    setLoading(true);
    setError(undefined);
    try {
      const nextStories = await fetchStories();
      setStories(nextStories);
      setSelectedId((current) => current ?? nextStories[0]?.story_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "API unavailable");
    } finally {
      setLoading(false);
    }
  }

  async function refreshSlate() {
    setLoading(true);
    setError(undefined);
    try {
      const nextStories = await refreshStories();
      setStories(nextStories);
      setSelectedId(nextStories[0]?.story_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Refresh failed");
    } finally {
      setLoading(false);
    }
  }

  async function buildDraft(storyId = selectedStory?.story_id) {
    if (!storyId) return;
    setDrafting(true);
    setError(undefined);
    try {
      const [
        nextPackage,
        nextQA,
        nextClaims,
        nextRights,
        nextPlatform,
        nextApproval,
        nextPublishPacket,
        nextStoryboard,
        nextDecision,
        nextOverrides
      ] = await Promise.all([
        generatePackage(storyId),
        fetchQA(storyId),
        fetchClaims(storyId),
        fetchRights(storyId),
        fetchPlatformReadiness(storyId),
        fetchApproval(storyId),
        fetchPublishPacket(storyId),
        fetchStoryboard(storyId),
        fetchDecision(storyId),
        fetchOverrides(storyId)
      ]);
      setVideoPackage(nextPackage);
      setQa(nextQA);
      setClaims(nextClaims);
      setRights(nextRights);
      setPlatform(nextPlatform);
      setApproval(nextApproval);
      setPublishPacket(nextPublishPacket);
      setStoryboard(nextStoryboard);
      setDecision(nextDecision);
      setOverrides(nextOverrides);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Draft failed");
    } finally {
      setDrafting(false);
    }
  }

  async function saveDecision(nextDecision: Exclude<EditorialDecisionValue, "pending">, notes: string) {
    if (!selectedStory) return;
    setError(undefined);
    try {
      const saved = await recordDecision(selectedStory.story_id, nextDecision, notes);
      setDecision(saved);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Decision failed");
    }
  }

  async function savePrimarySourceOverride(reason: string, evidenceUrl: string) {
    if (!selectedStory) return;
    setError(undefined);
    try {
      await recordPrimarySourceOverride(selectedStory.story_id, reason, evidenceUrl);
      await buildDraft(selectedStory.story_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Override failed");
    }
  }

  return (
    <main className="appShell">
      <header className="topBar">
        <div>
          <p className="eyebrow">Market Signal Studio</p>
          <h1>Editorial Signal Desk</h1>
        </div>
        <div className="topActions">
          <button className="iconButton" onClick={refreshSlate} title="Refresh story slate" aria-label="Refresh story slate">
            <RefreshCw size={18} />
            <span>{loading ? "Loading" : "Refresh"}</span>
          </button>
          <button className="iconButton primary" onClick={() => buildDraft()} title="Generate draft" aria-label="Generate draft">
            <Wand2 size={18} />
            <span>Draft</span>
          </button>
        </div>
      </header>

      {error ? <div className="errorBanner">{error}</div> : null}

      <section className="deskGrid">
        <StoryQueue stories={stories} selectedId={selectedStory?.story_id} onSelect={setSelectedId} />

        <section className="workbench">
          {selectedStory ? (
            <>
              <div className="storyHero">
                <div>
                  <span className={`statePill ${selectedStory.editorial_state}`}>
                    {selectedStory.editorial_state.replace("_", " ")}
                  </span>
                  <h2>{selectedStory.headline}</h2>
                  <div className="entityRow">
                    <strong>{selectedStory.primary_entity.ticker}</strong>
                    <span>{selectedStory.primary_entity.name}</span>
                    {selectedStory.supporting_entities.map((entity) => (
                      <em key={entity}>{entity}</em>
                    ))}
                  </div>
                </div>
                <ScoreMeter value={selectedStory.scores.story_score} label="story score" large />
              </div>

              <div className="insightGrid">
                <SignalChart story={selectedStory} />
                <div className="anglePanel">
                  <div className="miniHeader">
                    <ShieldCheck size={18} />
                    <span>Editorial Angles</span>
                  </div>
                  <div className="angleChips">
                    {selectedStory.angles.map((angle) => (
                      <span key={angle}>{angle}</span>
                    ))}
                  </div>
                  <div className="scoreStack">
                    {scoreLabels.map(([key, label]) => (
                      <div key={key}>
                        <span>{label}</span>
                        <strong>{Math.round(selectedStory.scores[key] * 100)}</strong>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <section className="sourcePanel">
                <div className="panelHeader compact">
                  <div>
                    <p className="eyebrow">Evidence</p>
                    <h2>Source Trail</h2>
                  </div>
                </div>
                <SourceTrail items={selectedStory.source_trail} />
              </section>
            </>
          ) : (
            <div className="emptyWorkbench">Backend story slate is empty.</div>
          )}
        </section>

        <DraftPanel
          videoPackage={videoPackage}
          qa={qa}
          claims={claims}
          rights={rights}
          platform={platform}
          approval={approval}
          publishPacket={publishPacket}
          storyboard={storyboard}
          decision={decision}
          overrides={overrides}
          storyId={selectedStory?.story_id}
          onDecision={saveDecision}
          onOverride={savePrimarySourceOverride}
          onGenerate={() => buildDraft()}
          loading={drafting}
        />
      </section>
    </main>
  );
}
