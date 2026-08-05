"""Output formatter — converts internal dicts to submission JSON.

Owner: Member C
"""

import json
from pathlib import Path
from typing import Any

from src.config import OUTPUT_DIR


def format_output(case_output: dict) -> dict:
    """Ensure output dict matches the exact submission schema."""
    # TODO: Member C implements this
    # Ensure all required keys exist
    # Ensure correct types and null handling
    return case_output


def save_output(case_id: str, case_output: dict) -> Path:
    """Save a case output to the output directory."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{case_id}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(case_output, f, indent=2, ensure_ascii=False)
    return output_path


def save_all_outputs(outputs: dict[str, dict]) -> list[Path]:
    """Save all case outputs."""
    paths = []
    for case_id, output in sorted(outputs.items()):
        paths.append(save_output(case_id, output))
    return paths
