# FileAnalyzer — Documentation

## What FileAnalyzer does
FileAnalyzer is a forensic-style toolkit focused on extracting, analyzing, and reporting on files in a directory tree. Key features:
- Inventory & hashing of files for deterministic identification
- Text extraction, OCR, and entity extraction from documents
- Media processing: image thumbnails, PDF page rendering, video frame sampling
- Face detection and matching against labeled galleries, with persisted results
- Deterministic assistant ("Alfred") to query files by person
- Web-like reports (JSON/CSV/HTML) and a desktop GUI for exploration

## Quickstart (Windows PowerShell)
- Create a venv and install deps:
  - python -m venv .venv
  - .\.venv\Scripts\Activate.ps1
  - pip install -r requirements.txt
- Run unit tests:
  - pytest -q
- Run the GUI (if Tk installed):
  - python -c "from case_agent.gui.app import run_gui; run_gui()"
- Example full scan:
  - py -3 scripts/run_full_scan.py --root "C:/path/to/data" --gallery "C:/Projects/FileAnalyzer/Images" --out "C:/Projects/FileAnalyzer/reports" --limit 10

## Configuration
- Persistent config file: `case_agent_config.json` (keys include `PDF_VIEWER`, `SHOW_TOP_SUBJECTS`, `THUMB_RENDER_CONCURRENCY`)
- Environment variables used in scripts: see individual scripts; common ones: `EPSTEIN_HEADLESS`, `EPISTEIN_SKIP_INSTALL`

## Logging & Errors
- Logging uses module-level loggers; inspector can find files in repo for detailed logging calls.
- GUI errors are handled defensively to avoid crashes during test runs.

## Onboarding (30 Minutes)
1. Clone the repo and install deps.
2. Run `pytest -q` and fix any failing tests in your environment.
3. Run `python -c "from case_agent.gui.app import run_gui; run_gui()"` to open GUI (if available).
4. Inspect `scripts/run_full_scan.py` for an example pipeline invocation.

## Agent API & People Report

- Run a lightweight HTTP server exposing the local agent and reports:
  - `python -m case_agent.cli serve --host 127.0.0.1 --port 5000 --db ./file_analyzer.db`
  - Endpoints:
    - `GET /agent/find?query=...` — search extracted text for mentions
    - `GET /agent/query?query=...` — structured deterministic answer with facts/provenance
    - `GET /agent/synopsis` — case-level synopsis (uses Ollama if available)
    - `GET /reports/people` — returns aggregated people mention report

- Export a people-mention report from the CLI:
  - `python -m case_agent.cli people-report --db ./file_analyzer.db --out people.json --format json`

## Docs & Next Steps
See `docs/ARCHITECTURE.md`, `docs/DIAGRAMS/` and the project `MANIFEST.md` for deeper information and current TODOs.
