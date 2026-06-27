import { BarChart3, FileText, Radio } from "lucide-react";
import type { Story } from "../types";
import { ScoreMeter } from "./ScoreMeter";

interface StoryQueueProps {
  stories: Story[];
  selectedId?: string;
  onSelect: (storyId: string) => void;
}

export function StoryQueue({ stories, selectedId, onSelect }: StoryQueueProps) {
  return (
    <aside className="queue">
      <div className="panelHeader">
        <div>
          <p className="eyebrow">Slate</p>
          <h2>Signal Queue</h2>
        </div>
        <span className="countBadge">{stories.length}</span>
      </div>

      <div className="storyList">
        {stories.map((story) => (
          <button
            className={`storyCard ${story.story_id === selectedId ? "selected" : ""}`}
            key={story.story_id}
            onClick={() => onSelect(story.story_id)}
          >
            <div className="storyCardTop">
              <span className={`statePill ${story.editorial_state}`}>{formatState(story.editorial_state)}</span>
              <ScoreMeter value={story.scores.story_score} label="score" />
            </div>
            <h3>{story.headline}</h3>
            <div className="storyMeta">
              <span>
                <Radio size={14} />
                {story.primary_entity.ticker}
              </span>
              <span>
                <FileText size={14} />
                {story.primary_evidence.length || 0} primary
              </span>
              <span>
                <BarChart3 size={14} />
                {story.story_type.replaceAll("_", " ")}
              </span>
            </div>
          </button>
        ))}
      </div>
    </aside>
  );
}

function formatState(state: Story["editorial_state"]) {
  return state.replace("_", " ");
}

