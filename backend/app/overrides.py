from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from app.models import EditorialOverride


DEFAULT_OVERRIDE_LEDGER_PATH = Path(__file__).parents[2] / ".runtime" / "overrides.jsonl"
ALLOWED_OVERRIDE_TYPES = {"primary_source"}


class OverrideLedger:
    def __init__(self, path: Path | None = None) -> None:
        env_path = os.getenv("MARKET_SIGNAL_OVERRIDE_LEDGER")
        if path is not None:
            self.path = path
        elif env_path:
            self.path = Path(env_path)
        else:
            self.path = DEFAULT_OVERRIDE_LEDGER_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load_active(self) -> dict[str, list[EditorialOverride]]:
        overrides: dict[str, list[EditorialOverride]] = {}
        if not self.path.exists():
            return overrides
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                clean = line.strip()
                if not clean:
                    continue
                override = EditorialOverride(**json.loads(clean))
                if override.active:
                    overrides.setdefault(override.story_id, []).append(override)
        return overrides

    def append(self, override: EditorialOverride) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(override.to_dict(), sort_keys=True) + "\n")


def has_override(overrides: list[EditorialOverride | dict[str, Any]] | None, override_type: str) -> bool:
    return any(_field(override, "override_type") == override_type and bool(_field(override, "active", True)) for override in overrides or [])


def override_refs(overrides: list[EditorialOverride | dict[str, Any]] | None, override_type: str) -> list[str]:
    refs = []
    for override in overrides or []:
        if _field(override, "override_type") == override_type and bool(_field(override, "active", True)):
            refs.append(f"override:{_field(override, 'created_at')}")
    return refs


def serialize_overrides(overrides: list[EditorialOverride | dict[str, Any]] | None) -> list[dict[str, object]]:
    result = []
    for override in overrides or []:
        if isinstance(override, EditorialOverride):
            result.append(override.to_dict())
        else:
            result.append(dict(override))
    return result


def validate_override(override_type: str, editor: str, reason: str, evidence_url: str) -> None:
    if override_type not in ALLOWED_OVERRIDE_TYPES:
        raise ValueError(f"override_type must be one of: {', '.join(sorted(ALLOWED_OVERRIDE_TYPES))}")
    if not editor.strip():
        raise ValueError("editor is required for an editorial override")
    if len(reason.strip()) < 20:
        raise ValueError("override reason must explain the editorial judgment in at least 20 characters")
    if not evidence_url.strip().startswith(("http://", "https://", "internal://")):
        raise ValueError("override evidence_url must be an http(s) URL or internal:// reference")


def _field(override: EditorialOverride | dict[str, Any], name: str, default: Any = None) -> Any:
    if isinstance(override, EditorialOverride):
        return getattr(override, name, default)
    return override.get(name, default)
