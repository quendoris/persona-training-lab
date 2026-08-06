from __future__ import annotations

import argparse
import json
from pathlib import Path

from persona_training_lab.i18n.audit import (
    build_audit_report,
    render_text_report,
)
from persona_training_lab.i18n.catalog import CatalogValidationError


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "persona_training_lab"
CATALOGS = SRC / "i18n" / "catalogs"


def run(*, strict_ui_literals: bool, as_json: bool) -> int:
    try:
        report = build_audit_report(
            catalog_directory=CATALOGS,
            source_root=SRC,
            display_root=ROOT,
            base_locale="ru-RU",
            strict_ui_literals=strict_ui_literals,
        )
    except CatalogValidationError as error:
        if as_json:
            print(
                json.dumps(
                    {"passed": False, "error": str(error)},
                    ensure_ascii=False,
                )
            )
        else:
            print(f"i18n audit failed: {error}")
        return 1

    if as_json:
        print(
            json.dumps(
                report.to_payload(),
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(render_text_report(report))
    return 0 if report.passed else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate complete PTL locale catalogs and UI text usage.",
    )
    parser.add_argument(
        "--strict-ui-literals",
        action="store_true",
        help="Fail when user-visible widget text remains hard-coded.",
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    return run(
        strict_ui_literals=args.strict_ui_literals,
        as_json=args.json,
    )


if __name__ == "__main__":
    raise SystemExit(main())
