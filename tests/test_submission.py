"""Hard-gate tests for the final grader archive."""

from __future__ import annotations

import zipfile
from pathlib import Path

from src.config import ROOT_DIR
from src.submission import EXPECTED_FILENAMES, create_submission_zip


def test_submission_zip_has_exact_root_level_layout() -> None:
    destination = ROOT_DIR / ".submission-test.zip"
    try:
        path, digest = create_submission_zip(destination)

        assert path == destination.resolve()
        assert len(digest) == 64
        with zipfile.ZipFile(path) as archive:
            assert archive.namelist() == list(EXPECTED_FILENAMES)
            assert all(
                "/" not in name and "\\" not in name
                for name in archive.namelist()
            )
    finally:
        destination.unlink(missing_ok=True)
