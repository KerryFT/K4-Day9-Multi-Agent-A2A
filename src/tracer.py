"""Trace logging and metadata generation.

Writes trace.jsonl and metadata.json for submission.

Owner: Member A
"""

import json
import time
from pathlib import Path
from typing import Any
from datetime import datetime

from src.config import LOGGING_DIR, AGENT_MODELS, AGENT_PROVIDERS


class Tracer:
    """Records agent traces and writes to trace.jsonl."""

    def __init__(self):
        self.traces: list[dict] = []
        self.start_time: float = time.time()

    def log_agent_call(
        self,
        case_id: str,
        agent_name: str,
        input_data: dict,
        output_data: dict,
        duration_ms: float,
    ) -> None:
        """Log a single agent invocation."""
        self.traces.append({
            "timestamp": datetime.now().isoformat(),
            "case_id": case_id,
            "agent": agent_name,
            "model": AGENT_MODELS.get(agent_name, "unknown"),
            "provider": AGENT_PROVIDERS.get(agent_name, "unknown"),
            "input_keys": list(input_data.keys()),
            "output_keys": list(output_data.keys()),
            "duration_ms": round(duration_ms, 2),
        })

    def save_trace(self) -> None:
        """Write all traces to trace.jsonl (overwrites, not append)."""
        trace_path = LOGGING_DIR / "trace.jsonl"
        with open(trace_path, "w", encoding="utf-8") as f:
            for trace in self.traces:
                f.write(json.dumps(trace, ensure_ascii=False) + "\n")

    def save_metadata(self) -> None:
        """Write metadata.json with model and runtime info."""
        metadata = {
            "models": AGENT_MODELS,
            "providers": AGENT_PROVIDERS,
            "framework": "custom-python",
            "language": "python",
            "parameter_sizes": {
                "qwen2.5:7b": "7B",
                "llama-3.1-8b-instant": "8B",
                "gemma2-9b-it": "9B",
            },
            "total_runtime_seconds": round(time.time() - self.start_time, 2),
            "total_cases": len(set(t["case_id"] for t in self.traces)),
            "generated_at": datetime.now().isoformat(),
        }
        metadata_path = LOGGING_DIR / "metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
