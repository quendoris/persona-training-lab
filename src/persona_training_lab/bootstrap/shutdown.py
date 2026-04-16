from __future__ import annotations

import logging


def run_shutdown_hooks() -> None:
    logging.getLogger(__name__).info("Shutdown hooks completed.")
