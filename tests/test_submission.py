"""Hard-gate tests for the final grader archive."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from src.config import ROOT_DIR
from src.submission import EXPECTED_FILENAMES, create_submission_zip


@pytest.mark.parametrize("include_output_directory", [False, True])
def test_submission_zip_has_exact_layout(include_output_directory: bool) -> None:
    suffix = "folder" if include_output_directory else "root"
    destination = ROOT_DIR / f".submission-{suffix}-test.zip"
    try:
        path, digest = create_submission_zip(
            destination,
            include_output_directory=include_output_directory,
        )

        assert path == destination.resolve()
        assert len(digest) == 64
        with zipfile.ZipFile(path) as archive:
            expected = [
                f"output/{name}" if include_output_directory else name
                for name in EXPECTED_FILENAMES
            ]
            assert archive.namelist() == expected
    finally:
        destination.unlink(missing_ok=True)
