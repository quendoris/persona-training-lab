from __future__ import annotations

from pathlib import Path

from tools.typing_audit import (
    classify_typing_suppressions,
    scan_typing_suppressions,
)


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


def test_typing_audit_inventories_coded_test_ignore_without_blocking(
    tmp_path: Path,
) -> None:
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "adapter.py").write_text(
        "value = object()  # type: ignore[arg-type]\n",
        encoding="utf-8",
    )

    findings = scan_typing_suppressions(
        root=tmp_path,
        code_roots=(tests_root,),
        config_paths=(),
    )
    blocking, informational = classify_typing_suppressions(findings)

    assert blocking == ()
    assert len(informational) == 1
    assert informational[0].path == "tests/adapter.py"
    assert informational[0].text == "# type: ignore[arg-type]"


def test_typing_audit_blocks_bare_or_file_wide_test_suppressions(
    tmp_path: Path,
) -> None:
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "hidden.py").write_text(
        "# mypy: ignore-errors\n"
        "first = object()  # type: ignore\n"
        "# mypy: disable-error-code=assignment\n",
        encoding="utf-8",
    )

    findings = scan_typing_suppressions(
        root=tmp_path,
        code_roots=(tests_root,),
        config_paths=(),
    )
    blocking, informational = classify_typing_suppressions(findings)

    assert [item.kind for item in blocking] == [
        "mypy_ignore_errors",
        "type_ignore",
        "mypy_disable_error_code",
    ]
    assert informational == ()


def test_typing_audit_blocks_coded_ignore_outside_tests(tmp_path: Path) -> None:
    source_root = tmp_path / "src"
    source_root.mkdir()
    (source_root / "production.py").write_text(
        "value = object()  # type: ignore[arg-type]\n",
        encoding="utf-8",
    )

    findings = scan_typing_suppressions(
        root=tmp_path,
        code_roots=(source_root,),
        config_paths=(),
    )
    blocking, informational = classify_typing_suppressions(findings)

    assert len(blocking) == 1
    assert blocking[0].path == "src/production.py"
    assert informational == ()
