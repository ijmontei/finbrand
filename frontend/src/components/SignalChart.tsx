import type { Story } from "../types";
import { chartPreviewUrl } from "../api";

interface SignalChartProps {
  story: Story;
}

const keys = [
  ["market_impact", "Market"],
  ["novelty", "Novelty"],
  ["source_authority", "Authority"],
  ["explainability", "Explainable"]
] as const;

export function SignalChart({ story }: SignalChartProps) {
  const move = Number(story.metrics.price_change_pct ?? 0);
  const volume = Number(story.metrics.volume_vs_20d ?? 1);

  return (
    <div className="signalChart">
      <div className="chartPreview">
        <img src={chartPreviewUrl(story.story_id)} alt={`${story.headline} signal chart`} />
      </div>
      <div className="metricTiles">
        <div>
          <span>Move</span>
          <strong>{move}%</strong>
        </div>
        <div>
          <span>Volume</span>
          <strong>{volume}x</strong>
        </div>
      </div>
      <div className="scoreBars">
        {keys.map(([key, label]) => (
          <div className="scoreBar" key={key}>
            <span>{label}</span>
            <div>
              <b style={{ width: `${Math.round(story.scores[key] * 100)}%` }} />
            </div>
            <em>{Math.round(story.scores[key] * 100)}</em>
          </div>
        ))}
      </div>
    </div>
  );
}
