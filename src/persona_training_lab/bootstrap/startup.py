from __future__ import annotations

import logging


def run_startup_checks() -> None:
    logging.getLogger(__name__).info("Startup checks completed.")
