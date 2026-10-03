from __future__ import annotations

from io import BytesIO
from pathlib import Path
import tarfile
import zipfile

from tools.package_audit import audit_package


def _seed_source(root: Path) -> None:
    (root / "docs").mkdir(parents=True)
    (root / "docs/quickstart.md").write_text("# Quickstart\n", encoding="utf-8")

    package = root / "src/persona_training_lab"
    (package / "i18n/catalogs/ru-RU").mkdir(parents=True)
    (package / "i18n/catalogs/ru-RU.json").write_text("{}\n", encoding="utf-8")
    (package / "i18n/catalogs/ru-RU/shell.json").write_text("{}\n", encoding="utf-8")
    (package / "ui/assets/icons").mkdir(parents=True)
    (package / "ui/assets/icons/example.svg").write_text("<svg/>\n", encoding="utf-8")
    (package / "__init__.py").write_text('__version__ = "0.1.0"\n', encoding="utf-8")

    (root / "pyproject.toml").write_text(
        "[project]\n"
        'name = "persona-training-lab"\n'
        'version = "0.1.0"\n',
        encoding="utf-8",
    )


def _write_sdist(path: Path, *, include_legal: bool = True) -> None:
    with tarfile.open(path, "w:gz") as archive:
        names = ["README.md"]
        if include_legal:
            names.extend(["LICENSE", "NOTICE", "AUTHORS"])
        for name in names:
            data = b"x\n"
            info = tarfile.TarInfo(f"persona_training_lab-0.1.0/{name}")
            info.size = len(data)
            archive.addfile(info, BytesIO(data))


def _write_wheel(
    path: Path,
    *,
    include_docs: bool = True,
    metadata_version: str = "0.1.0",
) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("persona_training_lab/__init__.py", '__version__ = "0.1.0"\n')
        archive.writestr("persona_training_lab/i18n/catalogs/ru-RU.json", "{}\n")
        archive.writestr("persona_training_lab/i18n/catalogs/ru-RU/shell.json", "{}\n")
        archive.writestr("persona_training_lab/ui/assets/icons/example.svg", "<svg/>\n")
        if include_docs:
            archive.writestr("persona_training_lab/docs/quickstart.md", "# Quickstart\n")

        dist_info = "persona_training_lab-0.1.0.dist-info"
        archive.writestr(
            f"{dist_info}/METADATA",
            "Metadata-Version: 2.4\n"
            "Name: persona-training-lab\n"
            f"Version: {metadata_version}\n\n",
        )
        for name in ("LICENSE", "NOTICE", "AUTHORS"):
            archive.writestr(f"{dist_info}/licenses/{name}", "x\n")


def _seed_dist(root: Path, **wheel_kwargs: object) -> Path:
    dist = root / "dist"
    dist.mkdir()
    _write_wheel(
        dist / "persona_training_lab-0.1.0-py3-none-any.whl",
        **wheel_kwargs,
    )
    _write_sdist(dist / "persona_training_lab-0.1.0.tar.gz")
    return dist


def test_package_audit_accepts_matching_wheel_and_sdist(tmp_path: Path) -> None:
    _seed_source(tmp_path)
    dist = _seed_dist(tmp_path)

    payload = audit_package(tmp_path, dist)

    assert payload["passed"] is True
    assert payload["wheel_metadata_name"] == "persona-training-lab"
    assert payload["wheel_metadata_version"] == "0.1.0"
    assert payload["missing_wheel_files"] == []
    assert payload["missing_wheel_legal"] == []
    assert payload["missing_sdist_legal"] == []


def test_package_audit_rejects_missing_bundled_documentation(tmp_path: Path) -> None:
    _seed_source(tmp_path)
    dist = _seed_dist(tmp_path, include_docs=False)

    payload = audit_package(tmp_path, dist)

    assert payload["passed"] is False
    assert payload["missing_wheel_files"] == [
        "persona_training_lab/docs/quickstart.md"
    ]


def test_package_audit_rejects_metadata_version_drift(tmp_path: Path) -> None:
    _seed_source(tmp_path)
    dist = _seed_dist(tmp_path, metadata_version="0.1.1")

    payload = audit_package(tmp_path, dist)

    assert payload["passed"] is False
    assert payload["wheel_metadata_version"] == "0.1.1"
