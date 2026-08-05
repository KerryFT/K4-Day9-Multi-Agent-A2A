"""Validate and package the grader submission with a strict ZIP layout.

The grader requires exactly ``EC_001.json`` through ``EC_050.json`` at the
archive root.  Repository placeholders such as ``output/.gitkeep`` must never
be included.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from src.config import OUTPUT_DIR, ROOT_CAUSE_CODES
from src.models import CaseOutput
from src.utils.validators import validate_full_output


EXPECTED_FILENAMES = tuple(f"EC_{index:03d}.json" for index in range(1, 51))


class SubmissionValidationError(ValueError):
    """Raised when an output or submission archive fails a hard gate."""


def _reject_non_finite(value: str) -> None:
    raise SubmissionValidationError(f"Non-finite JSON number: {value}")


def _check_finite_numbers(value: Any, path: str = "$") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise SubmissionValidationError(f"Non-finite number at {path}")
    if isinstance(value, dict):
        for key, child in value.items():
            _check_finite_numbers(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _check_finite_numbers(child, f"{path}[{index}]")


def validate_output_file(path: Path) -> dict[str, Any]:
    """Apply strict JSON, filename, schema, and business-rule gates."""
    try:
        raw = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=_reject_non_finite,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SubmissionValidationError(f"Invalid JSON {path.name}: {exc}") from exc

    _check_finite_numbers(raw)
    expected_case_id = path.stem
    if raw.get("case_id") != expected_case_id:
        raise SubmissionValidationError(
            f"{path.name}: case_id must be {expected_case_id!r}"
        )

    try:
        canonical = CaseOutput.model_validate(raw).to_json_dict()
    except Exception as exc:
        raise SubmissionValidationError(
            f"{path.name}: output schema validation failed: {exc}"
        ) from exc

    valid, errors = validate_full_output(canonical)
    if not valid:
        raise SubmissionValidationError(f"{path.name}: {'; '.join(errors)}")

    valid_policy_ids = {f"policy:{code}" for code in ROOT_CAUSE_CODES.values()}
    invalid_policy_ids = {
        evidence
        for evidence in canonical["evidence_ids"]
        if evidence.startswith("policy:") and evidence not in valid_policy_ids
    }
    if invalid_policy_ids:
        raise SubmissionValidationError(
            f"{path.name}: invalid policy evidence {sorted(invalid_policy_ids)}"
        )
    return canonical


def validate_output_directory(output_dir: Path = OUTPUT_DIR) -> list[Path]:
    """Return the 50 validated JSON paths in canonical case order."""
    actual_json_names = {path.name for path in output_dir.glob("*.json")}
    expected_names = set(EXPECTED_FILENAMES)
    missing = sorted(expected_names - actual_json_names)
    extra = sorted(actual_json_names - expected_names)
    if missing or extra:
        raise SubmissionValidationError(
            f"Output JSON set mismatch; missing={missing}, extra={extra}"
        )

    paths = [output_dir / name for name in EXPECTED_FILENAMES]
    for path in paths:
        validate_output_file(path)
    return paths


def create_submission_zip(
    destination: Path,
    output_dir: Path = OUTPUT_DIR,
) -> tuple[Path, str]:
    """Atomically build and re-open a root-level archive of exactly 50 JSONs."""
    paths = validate_output_directory(output_dir)
    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        prefix=f".{destination.stem}-",
        suffix=".tmp",
        dir=destination.parent,
        delete=False,
    ) as temporary:
        temporary_path = Path(temporary.name)

    try:
        with zipfile.ZipFile(
            temporary_path,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            for path in paths:
                archive.write(path, arcname=path.name)

        with zipfile.ZipFile(temporary_path, mode="r") as archive:
            names = archive.namelist()
            if names != list(EXPECTED_FILENAMES):
                raise SubmissionValidationError(
                    "ZIP layout must contain exactly 50 JSON files at archive root"
                )
            for info in archive.infolist():
                if info.is_dir() or "/" in info.filename or "\\" in info.filename:
                    raise SubmissionValidationError(
                        f"Nested or directory ZIP entry is forbidden: {info.filename}"
                    )
                validate_output_file_from_bytes(info.filename, archive.read(info))

        temporary_path.replace(destination)
    finally:
        temporary_path.unlink(missing_ok=True)

    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    return destination, digest


def validate_output_file_from_bytes(filename: str, payload: bytes) -> None:
    """Re-validate an archived member without trusting the source file."""
    try:
        raw = json.loads(payload.decode("utf-8"), parse_constant=_reject_non_finite)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise SubmissionValidationError(f"Invalid archived JSON {filename}: {exc}") from exc
    _check_finite_numbers(raw)
    if raw.get("case_id") != Path(filename).stem:
        raise SubmissionValidationError(f"Archived case_id mismatch in {filename}")
    CaseOutput.model_validate(raw)
    valid, errors = validate_full_output(raw)
    if not valid:
        raise SubmissionValidationError(f"{filename}: {'; '.join(errors)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Directory containing EC_001.json through EC_050.json",
    )
    parser.add_argument(
        "--destination",
        type=Path,
        default=OUTPUT_DIR.parent / "output_submission.zip",
        help="Destination ZIP path",
    )
    args = parser.parse_args()
    path, digest = create_submission_zip(args.destination, args.output_dir)
    print(f"submission={path}")
    print(f"entries={len(EXPECTED_FILENAMES)}")
    print(f"sha256={digest}")


if __name__ == "__main__":
    main()
