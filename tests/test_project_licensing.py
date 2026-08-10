from __future__ import annotations

from hashlib import sha1
from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_AGPL_V3_GIT_BLOB = "dba13ed2ddf783ee8118c6a581dbf75305f816a3"
PROVENANCE = "This project was created by one human and one neural network."


def _git_blob_sha(path: Path) -> str:
    payload = path.read_bytes()
    header = f"blob {len(payload)}\0".encode()
    return sha1(header + payload).hexdigest()  # noqa: S324 - integrity fixture


def test_canonical_agpl_text_is_not_modified() -> None:
    assert _git_blob_sha(ROOT / "LICENSE") == CANONICAL_AGPL_V3_GIT_BLOB


def test_distribution_metadata_includes_legal_files() -> None:
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]

    assert metadata["license"] == "AGPL-3.0-only"
    assert metadata["license-files"] == ["LICENSE", "NOTICE", "AUTHORS"]


def test_original_project_provenance_is_explicit_and_anonymous() -> None:
    notice = (ROOT / "NOTICE").read_text(encoding="utf-8")
    authors = (ROOT / "AUTHORS").read_text(encoding="utf-8")

    assert PROVENANCE in notice
    assert PROVENANCE in authors
    assert "One Human" in authors
    assert "One Neural Network" in authors
    assert "not presented as a legal person" in notice
