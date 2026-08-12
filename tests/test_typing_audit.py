from __future__ import annotations

from pathlib import Path

from tools.typing_audit import scan_typing_suppressions


def test_typing_audit_accepts_clean_source_and_config(tmp_path: Path) -> None:
    source_root = tmp_path / "src"
    source_root.mkdir()
    (source_root / "clean.py").write_text(
        "def answer(value: int) -> int:\n    return value + 1\n",
        encoding="utf-8",
    )
    config = tmp_path / "pyproject.toml"
    config.write_text(
        "[tool.mypy]\nwarn_unused_ignores = true\n",
        encoding="utf-8",
    )

    findings = scan_typing_suppressions(
        root=tmp_path,
        code_roots=(source_root,),
        config_paths=(config,),
    )

    assert findings == ()


def test_typing_audit_reports_source_suppressions(tmp_path: Path) -> None:
    source_root = tmp_path / "src"
    source_root.mkdir()
    source = source_root / "hidden.py"
    source.write_text(
        "# mypy: ignore-errors\n"
        "value = object()  # type: ignore[arg-type]\n"
        "# mypy: disable-error-code=assignment\n",
        encoding="utf-8",
    )

    findings = scan_typing_suppressions(
        root=tmp_path,
        code_roots=(source_root,),
        config_paths=(),
    )

    assert [item.kind for item in findings] == [
        "mypy_ignore_errors",
        "type_ignore",
        "mypy_disable_error_code",
    ]
    assert [item.line for item in findings] == [1, 2, 3]
    assert {item.path for item in findings} == {"src/hidden.py"}


def test_typing_audit_ignores_suppression_text_inside_strings(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "tests"
    source_root.mkdir()
    (source_root / "fixture.py").write_text(
        'payload = "value = object()  # type: ignore[arg-type]"\n'
        'pragma = "# mypy: ignore-errors"\n',
        encoding="utf-8",
    )

    findings = scan_typing_suppressions(
        root=tmp_path,
        code_roots=(source_root,),
        config_paths=(),
    )

    assert findings == ()


def test_typing_audit_reports_config_suppressions(tmp_path: Path) -> None:
    source_root = tmp_path / "src"
    source_root.mkdir()
    config = tmp_path / "mypy.ini"
    config.write_text(
        "[mypy]\n"
        "ignore_errors = true\n"
        "disable_error_code = assignment, arg-type\n",
        encoding="utf-8",
    )

    findings = scan_typing_suppressions(
        root=tmp_path,
        code_roots=(source_root,),
        config_paths=(config,),
    )

    assert [(item.kind, item.line) for item in findings] == [
        ("mypy_ignore_errors_config", 2),
        ("mypy_disable_error_code_config", 3),
    ]
    assert {item.path for item in findings} == {"mypy.ini"}
