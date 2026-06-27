import { Gauge } from "lucide-react";
import type { CSSProperties } from "react";

interface ScoreMeterProps {
  value: number;
  label: string;
  large?: boolean;
}

export function ScoreMeter({ value, label, large = false }: ScoreMeterProps) {
  const pct = Math.round(value * 100);
  return (
    <div className={large ? "score scoreLarge" : "score"}>
      <div className="scoreDial" style={{ "--score": pct } as CSSProperties}>
        <Gauge size={large ? 22 : 16} />
        <strong>{pct}</strong>
      </div>
      <span>{label}</span>
    </div>
  );
}
