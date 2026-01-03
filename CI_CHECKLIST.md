CI Checklist — Make repository CI-friendly

Purpose: Ensure tests and report generation run reliably on CI (Windows runner) and in headless environments.

1) Base environment
- Use Windows runner (GitHub Actions `windows-latest` or self-hosted Windows). Python 3.11 is required.
- Create and activate a venv at the project root or use the runner's Python virtualenv support.

2) Install Python dependencies
- pip install --upgrade pip setuptools wheel
- pip install -r requirements.txt
- pip install -r case_agent/requirements.txt
- pip install pytest
- (Optional) Install development helpers: flake8, mypy, isort

3) System binaries (Windows)
- Ensure Tcl/Tk runtime is available (Python on Windows typically ships with Tcl/Tk). If using a minimal Python or container, install Tcl/Tk or set TCL_LIBRARY/TK_LIBRARY to a bundled runtime.
- FFmpeg (for media pipelines) — install via winget or package manager
- Tesseract-OCR (for OCR) — install via winget

4) Headless GUI handling
- Tests now tolerate missing Tcl/Tk: `case_agent.gui.run_gui()` detects non-interactive Tk roots and falls back to a minimal headless structure used by tests.
- CI should still prefer to have Tcl/Tk available, but GUI tests will pass in headless environments due to the fallback.

5) Test steps (example CI job)
- Set up Python 3.11
- pip install -r requirements.txt
- pip install -r case_agent/requirements.txt
- (Optional) set env vars for Tcl/Tk if needed: $env:TCL_LIBRARY, $env:TK_LIBRARY
- Run: python -m pytest -q
- Generate reports: python -c "import sys; sys.path.insert(0, r'C:\Projects\FileAnalyzer'); from scripts.generate_reports import main; main()"
- Upload reports/artifacts as CI artifacts

6) Caching and speed
- Cache pip wheel cache and the venv where supported
- Cache spaCy model (`en_core_web_sm`) or install as part of setup step: `python -m spacy download en_core_web_sm` (or include it in an image)

7) Linting and static checks (optional but recommended)
- Run flake8 and mypy as separate jobs if desired
- Enforce black formatting (pre-commit hooks recommended)

8) Security and secrets
- DO NOT use cloud API keys or external network creds in CI
- For optional tests that require external APIs, mark them with pytest markers and only run them in special jobs with secrets

9) Artifacts
- Save generated `reports/` (JSON/HTML/CSV) and `artifacts/manifests/` as job artifacts for inspection

10) Example GitHub Actions hints
- Use a matrix job with Windows/Python-3.11
- Add a caching step for pip
- Add an artifact upload step for `reports/`

Notes:
- The repo includes a `tcl/` folder to help run GUI tests in some environments; however, a full Tcl/Tk install is preferred for complete GUI functionality.
- The codebase contains a headless fallback to support CI and headless runners. Tests have been updated to be robust when Tcl/Tk is missing.
