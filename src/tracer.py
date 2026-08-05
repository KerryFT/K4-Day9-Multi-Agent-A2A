"""
Trace logger and metadata generator.

Records every agent invocation during a pipeline run and persists:

- ``logging/trace.jsonl``   — one JSON line per agent call (overwritten each run)
- ``logging/metadata.json`` — model names, parameter sizes, runtime stats

Owner: Member A
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from src.config import AGENT_MODELS, AGENT_PROVIDERS, LOGGING_DIR


class Tracer:
    """Accumulates agent-call records and writes them at the end of a run."""

    def __init__(self) -> None:
        self._entries: list[dict[str, Any]] = []
        self._t0 = time.monotonic()
        self._started_at = datetime.now().isoformat()

    # ── Recording ─────────────────────────────────────────────────

    def log(
        self,
        case_id: str,
        agent_name: str,
        input_summary: dict[str, Any],
        output_summary: dict[str, Any],
        duration_ms: float,
        *,
        error: str | None = None,
    ) -> None:
        """Append one agent-invocation record.

        Args:
            case_id:        E.g. ``"EC_001"``.
            agent_name:     E.g. ``"customer"``, ``"policy"``.
            input_summary:  Dict summarising what was sent to the agent.
            output_summary: Dict summarising what the agent returned.
            duration_ms:    Wall-clock time in milliseconds.
            error:          Error message if the call failed, else None.
        """
        self._entries.append({
            "timestamp":  datetime.now().isoformat(),
            "case_id":    case_id,
            "agent":      agent_name,
            "model":      AGENT_MODELS.get(agent_name, "deterministic"),
            "provider":   AGENT_PROVIDERS.get(agent_name, "local"),
            "duration_ms": round(duration_ms, 2),
            "input_keys":  _keys(input_summary),
            "output_keys": _keys(output_summary),
            "error":       error,
        })

    # ── Persistence ───────────────────────────────────────────────

    def save_trace(self) -> Path:
        """Overwrite ``trace.jsonl`` with the current run (not append)."""
        LOGGING_DIR.mkdir(parents=True, exist_ok=True)
        path = LOGGING_DIR / "trace.jsonl"
        with open(path, "w", encoding="utf-8") as fh:
            for entry in self._entries:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return path

    def save_metadata(self) -> Path:
        """Write ``metadata.json`` with model and runtime information."""
        LOGGING_DIR.mkdir(parents=True, exist_ok=True)
        elapsed = time.monotonic() - self._t0
        unique_cases = {e["case_id"] for e in self._entries}

        metadata: dict[str, Any] = {
            "models":     AGENT_MODELS,
            "providers":  AGENT_PROVIDERS,
            "parameter_sizes": {
                "qwen2.5:7b":           "7B",
                "llama-3.1-8b-instant": "8B",
                "gemma2-9b-it":         "9B",
            },
            "framework":  "custom-python-multiagent",
            "language":   "python",
            "runtime": {
                "started_at":        self._started_at,
                "finished_at":       datetime.now().isoformat(),
                "total_seconds":     round(elapsed, 2),
                "total_cases":       len(unique_cases),
                "total_agent_calls": len(self._entries),
            },
        }

        path = LOGGING_DIR / "metadata.json"
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(metadata, fh, indent=2, ensure_ascii=False)
        return path

    # ── Diagnostics ───────────────────────────────────────────────

    @property
    def num_entries(self) -> int:
        return len(self._entries)

    @property
    def num_errors(self) -> int:
        return sum(1 for e in self._entries if e["error"] is not None)


# ── Internal ──────────────────────────────────────────────────────

def _keys(obj: Any) -> list[str]:
    """Extract sorted dict keys, tolerating non-dict inputs."""
    if isinstance(obj, dict):
        return sorted(obj.keys())
    return []
