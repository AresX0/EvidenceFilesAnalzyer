# Operations & Runbook

## Startup
- Create venv, install deps, (optionally) run Playwright install.
- For long runs, monitor logs and use `THUMB_RENDER_CONCURRENCY` to tune CPU usage.

## Running a full scan
- Use `scripts/run_full_scan.py` with `--root`, `--gallery`, `--out`, and optional `--limit`.
- Output reports are written to `reports/` by default.

## Troubleshooting
- Tk/Tcl errors: missing system Tk install; install the appropriate OS package or run in headless mode (some tests will skip GUI parts).
- Database locked or corrupt: ensure no conflicting writers; run DB vacuum and backup before large changes.

## Backup & Retention
- Keep backups of `case_agent_config.json` and `queue_state.json` if used by GUI.
