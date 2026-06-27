import { ExternalLink, ShieldCheck } from "lucide-react";
import type { SourceTrailItem } from "../types";

interface SourceTrailProps {
  items: SourceTrailItem[];
}

export function SourceTrail({ items }: SourceTrailProps) {
  return (
    <div className="sourceTrail">
      {items.map((item) => (
        <a href={item.url} target="_blank" rel="noreferrer" className="sourceItem" key={item.id}>
          <div className="sourceIcon">{item.primary_source ? <ShieldCheck size={18} /> : <ExternalLink size={18} />}</div>
          <div>
            <strong>{item.source_name}</strong>
            <span>{item.title}</span>
            <small>{item.license_notes}</small>
          </div>
        </a>
      ))}
    </div>
  );
}

