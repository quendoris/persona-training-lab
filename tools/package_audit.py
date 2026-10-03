from __future__ import annotations

import argparse
import json
import re
import tarfile
import tomllib
import zipfile
from email import policy
from email.parser import BytesParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIST = ROOT / "dist"
LEGAL_FILENAMES = frozenset({"LICENSE", "NOTICE", "AUTHORS"})


def _normalized_distribution_name(name: str) -> str:
    return re.sub(r"[-_.]+", "_", name.strip()).strip("_")


def _project_identity(root: Path) -> tuple[str, str]:
    payload = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    project = payload.get("project", {})
    return str(project.get("name", "")).strip(), str(project.get("version", "")).strip()


def _files_below(directory: Path) -> tuple[Path, ...]:
    if not directory.is_dir():
        return ()
    return tuple(
        sorted(
            (
                path
                for path in directory.rglob("*")
                if path.is_file() and "__pycache__" not in path.parts
            ),
            key=lambda path: path.as_posix(),
        )
    )


def _expected_wheel_files(root: Path) -> tuple[str, ...]:
    expected = {"persona_training_lab/__init__.py"}

    docs_root = root / "docs"
    for path in _files_below(docs_root):
        relative = path.relative_to(docs_root).as_posix()
        expected.add(f"persona_training_lab/docs/{relative}")

    source_root = root / "src"
    for package_root in (
        source_root / "persona_training_lab" / "i18n" / "catalogs",
        source_root / "persona_training_lab" / "ui" / "assets",
    ):
        for path in _files_below(package_root):
            expected.add(path.relative_to(source_root).as_posix())

    return tuple(sorted(expected))


def _wheel_metadata(
    archive: zipfile.ZipFile,
    names: set[str],
) -> tuple[str, str, str]:
    metadata_paths = sorted(
        name for name in names if name.endswith(".dist-info/METADATA")
    )
    if len(metadata_paths) != 1:
        return "", "", ""
    metadata_path = metadata_paths[0]
    message = BytesParser(policy=policy.default).parsebytes(
        archive.read(metadata_path)
    )
    return (
        metadata_path,
        str(message.get("Name") or "").strip(),
        str(message.get("Version") or "").strip(),
    )


def audit_package(root: Path = ROOT, dist_dir: Path | None = None) -> dict[str, object]:
    root = root.resolve()
    dist_dir = (dist_dir or (root / "dist")).resolve()
    project_name, version = _project_identity(root)
    distribution = _normalized_distribution_name(project_name)

    wheel_candidates = sorted(dist_dir.glob(f"{distribution}-{version}-*.whl"))
    sdist_candidates = sorted(dist_dir.glob(f"{distribution}-{version}.tar.gz"))

    payload: dict[str, object] = {
        "project_name": project_name,
        "version": version,
        "dist_dir": str(dist_dir),
        "wheel_candidates": [path.name for path in wheel_candidates],
        "sdist_candidates": [path.name for path in sdist_candidates],
        "wheel": "",
        "sdist": "",
        "wheel_metadata_path": "",
        "wheel_metadata_name": "",
        "wheel_metadata_version": "",
        "missing_wheel_files": [],
        "missing_wheel_legal": [],
        "missing_sdist_legal": [],
        "unexpected_wheel_repository_roots": [],
        "passed": False,
    }

    if len(wheel_candidates) != 1 or len(sdist_candidates) != 1:
        return payload

    wheel_path = wheel_candidates[0]
    sdist_path = sdist_candidates[0]
    payload["wheel"] = wheel_path.name
    payload["sdist"] = sdist_path.name

    expected_files = set(_expected_wheel_files(root))
    with zipfile.ZipFile(wheel_path) as archive:
        wheel_names = set(archive.namelist())
        metadata_path, metadata_name, metadata_version = _wheel_metadata(
            archive,
            wheel_names,
        )
    payload["wheel_metadata_path"] = metadata_path
    payload["wheel_metadata_name"] = metadata_name
    payload["wheel_metadata_version"] = metadata_version
    payload["missing_wheel_files"] = sorted(expected_files - wheel_names)

    wheel_legal = {Path(name).name for name in wheel_names} & LEGAL_FILENAMES
    payload["missing_wheel_legal"] = sorted(LEGAL_FILENAMES - wheel_legal)
    payload["unexpected_wheel_repository_roots"] = sorted(
        name
        for name in wheel_names
        if name.startswith("tests/") or name.startswith("tools/")
    )

    with tarfile.open(sdist_path, "r:gz") as archive:
        sdist_names = {member.name for member in archive.getmembers()}
    sdist_legal = {Path(name).name for name in sdist_names} & LEGAL_FILENAMES
    payload["missing_sdist_legal"] = sorted(LEGAL_FILENAMES - sdist_legal)

    payload["passed"] = bool(
        project_name
        and version
        and metadata_name == project_name
        and metadata_version == version
        and not payload["missing_wheel_files"]
        and not payload["missing_wheel_legal"]
        and not payload["missing_sdist_legal"]
        and not payload["unexpected_wheel_repository_roots"]
    )
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit PTL wheel/sdist contents after uv build.",
    )
    parser.add_argument("--dist", type=Path, default=DEFAULT_DIST)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    payload = audit_package(ROOT, args.dist)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"package audit: {'PASS' if payload['passed'] else 'FAIL'}")
        print(f"wheel: {payload['wheel'] or 'missing/ambiguous'}")
        print(f"sdist: {payload['sdist'] or 'missing/ambiguous'}")
        if payload["missing_wheel_files"]:
            print("missing wheel files:")
            for path in payload["missing_wheel_files"]:
                print(f"  - {path}")
        if payload["missing_wheel_legal"]:
            print("missing wheel legal files: " + ", ".join(payload["missing_wheel_legal"]))
        if payload["missing_sdist_legal"]:
            print("missing sdist legal files: " + ", ".join(payload["missing_sdist_legal"]))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
