from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from threading import RLock


_LOGGING_LOCK = RLock()
_HANDLER_MARKER = "persona_training_lab_managed"


def configure_logging(log_dir: Path | None = None) -> None:
    """Configure quiet console output and durable rotating application logs."""

    with _LOGGING_LOCK:
        root = logging.getLogger()
        root.setLevel(logging.INFO)

        for handler in tuple(root.handlers):
            if getattr(handler, _HANDLER_MARKER, False):
                root.removeHandler(handler)
                try:
                    handler.close()
                except Exception:
                    pass

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )

        # The terminal is reserved for failures that make the process unusable.
        # Recoverable UI/service errors belong in the rotating log and event log.
        console = logging.StreamHandler()
        console.setLevel(logging.CRITICAL)
        console.setFormatter(formatter)
        setattr(console, _HANDLER_MARKER, True)
        root.addHandler(console)

        if log_dir is None:
            return

        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                log_dir / "persona_training_lab.log",
                maxBytes=5_000_000,
                backupCount=5,
                encoding="utf-8",
            )
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)
            setattr(file_handler, _HANDLER_MARKER, True)
            root.addHandler(file_handler)
        except OSError:
            # Failure to create a diagnostic file must not prevent app startup.
            return
