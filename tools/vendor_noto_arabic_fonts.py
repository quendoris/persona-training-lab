from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ASSETS_ROOT = (
    REPOSITORY_ROOT
    / "src"
    / "persona_training_lab"
    / "ui"
    / "assets"
    / "fonts"
)
MANIFEST_PATH = ASSETS_ROOT / "noto_arabic_ui.json"
RAW_ROOT = "https://raw.githubusercontent.com"


def _git_blob_sha1(data: bytes) -> str:
    payload = f"blob {len(data)}\0".encode("ascii") + data
    return hashlib.sha1(payload, usedforsecurity=False).hexdigest()


def _load_manifest() -> dict[str, Any]:
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if payload.get("schema") != 1:
        raise RuntimeError("Unsupported Noto Arabic font manifest schema")
    return payload


def _verify_bytes(data: bytes, spec: dict[str, Any]) -> None:
    expected_size = int(spec["size"])
    if len(data) != expected_size:
        raise RuntimeError(
            f"{spec['filename']}: size mismatch: {len(data)} != {expected_size}"
        )
    actual_sha = _git_blob_sha1(data)
    expected_sha = str(spec["git_blob_sha1"])
    if actual_sha != expected_sha:
        raise RuntimeError(
            f"{spec['filename']}: Git blob SHA mismatch: "
            f"{actual_sha} != {expected_sha}"
        )


def _download(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "persona-training-lab-font-vendor"})
    with urlopen(request, timeout=60) as response:  # noqa: S310 - pinned HTTPS source
        return response.read()


def _source_url(manifest: dict[str, Any], spec: dict[str, Any]) -> str:
    upstream = manifest["upstream"]
    return (
        f"{RAW_ROOT}/{upstream['repository']}/{upstream['commit']}/"
        f"{spec['source_path']}"
    )


def _check_existing(manifest: dict[str, Any]) -> None:
    for spec in manifest["fonts"]:
        path = ASSETS_ROOT / str(spec["filename"])
        if not path.is_file():
            raise RuntimeError(f"Missing vendored font: {path}")
        data = path.read_bytes()
        _verify_bytes(data, spec)
        print(
            f"OK {path.name}: size={len(data)} "
            f"git_blob_sha1={_git_blob_sha1(data)} "
            f"sha256={hashlib.sha256(data).hexdigest()}"
        )


def _vendor(manifest: dict[str, Any]) -> None:
    ASSETS_ROOT.mkdir(parents=True, exist_ok=True)
    for spec in manifest["fonts"]:
        data = _download(_source_url(manifest, spec))
        _verify_bytes(data, spec)
        destination = ASSETS_ROOT / str(spec["filename"])
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        try:
            temporary.write_bytes(data)
            temporary.replace(destination)
        finally:
            if temporary.exists():
                temporary.unlink()
        print(
            f"Vendored {destination.name}: size={len(data)} "
            f"git_blob_sha1={_git_blob_sha1(data)} "
            f"sha256={hashlib.sha256(data).hexdigest()}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Vendor pinned Noto Sans Arabic UI fonts with integrity checks."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify existing vendored files without network access.",
    )
    args = parser.parse_args()

    manifest = _load_manifest()
    license_spec = manifest["license"]
    license_path = ASSETS_ROOT / str(license_spec["filename"])
    if not license_path.is_file():
        raise RuntimeError(f"Missing bundled font license: {license_path}")
    license_sha = _git_blob_sha1(license_path.read_bytes())
    if license_sha != str(license_spec["git_blob_sha1"]):
        raise RuntimeError(
            f"{license_path.name}: Git blob SHA mismatch: "
            f"{license_sha} != {license_spec['git_blob_sha1']}"
        )

    if args.check:
        _check_existing(manifest)
    else:
        _vendor(manifest)
        _check_existing(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
