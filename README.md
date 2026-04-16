# Persona Training Lab

Phase 1 scaffolding for the desktop-first research workstation.

## What is included
- layered package layout
- SQLite foundation
- local artifact manager
- workflow supervisor skeleton
- PySide6 main shell
- Dashboard, Docs and Style starter screens
- Velvet theme

## Quick start

```bash
uv sync --extra dev
uv run python -m persona_training_lab.bootstrap.app
```

## What you should see
- main window with left navigation
- Dashboard / Docs / Style workspaces
- right Inspector dock
- bottom Activity and Telemetry docks
- generated `app.db` plus `artifacts/`, `exports/`, `temp/`, `cache/`
