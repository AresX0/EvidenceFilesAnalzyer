# Developer Onboarding (30 Minutes)

Goal: get a new developer productive quickly with FileAnalyzer.

Prereqs
- Windows machine recommended for GUI development.
- Python 3.11+ installed.

Quick steps
1. Clone the repo and create a venv
   - git clone <repo>
   - cd FileAnalyzer
   - python -m venv .venv
   - .\.venv\Scripts\Activate.ps1
2. Install deps
   - pip install -r requirements.txt
   - (Optional) python -m playwright install
3. Run tests
   - pytest -q
   - Expect 43 passed, 1 skipped locally (GUI-skippable tests if Tk not available)
4. Try the GUI
   - python -c "from case_agent.gui.app import run_gui; run_gui()"
   - If Tk/Tcl missing, run in headless mode or run tests only.
5. Run a small scan (example)
   - py -3 scripts/run_full_scan.py --root "C:/path/to/evidence" --gallery "C:/Projects/FileAnalyzer/Images" --out "C:/Projects/FileAnalyzer/reports" --limit 10
6. Report generation
   - Generated reports go to `reports/` (JSON/CSV/HTML). See `docs/README.md` for details.

Developer tips
- Tests: isolate GUI-dependent tests using `case_agent.utils.tk_helper.is_tk_usable()`.
- Doc updates: add module docstrings and small function docstrings using the project's DOCSTYLE guidance.
- PRs: keep changes modular; add tests for any behavior changes.

Useful files
- scripts/run_full_scan.py — example end-to-end pipeline
- case_agent/gui/app.py — GUI entry point
- case_agent/reports.py — report writer (JSON/CSV/HTML)
- docs/ for architecture, diagrams and testing guides
