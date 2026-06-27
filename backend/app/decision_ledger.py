from __future__ import annotations

import json
import os
from pathlib import Path

from app.models import EditorialDecision


DEFAULT_LEDGER_PATH = Path(__file__).parents[2] / ".runtime" / "decisions.jsonl"


class DecisionLedger:
    def __init__(self, path: Path | None = None) -> None:
        env_path = os.getenv("MARKET_SIGNAL_DECISION_LEDGER")
        if path is not None:
            self.path = path
        elif env_path:
            self.path = Path(env_path)
        else:
            self.path = DEFAULT_LEDGER_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load_latest(self) -> dict[str, EditorialDecision]:
        decisions: dict[str, EditorialDecision] = {}
        if not self.path.exists():
            return decisions
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                clean = line.strip()
                if not clean:
                    continue
                payload = json.loads(clean)
                decision = EditorialDecision(**payload)
                decisions[decision.story_id] = decision
        return decisions

    def append(self, decision: EditorialDecision) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(decision.to_dict(), sort_keys=True) + "\n")
