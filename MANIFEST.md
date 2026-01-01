# MANIFEST — FileAnalyzer

## Mission & Status
Mission: Make FileAnalyzer fully documented, tested, and maintainable; add a mission scaffold to the repository. This project includes a GUI (Tkinter), pipelines for extraction and face search, reports and export, and an "Alfred" assistant front-end for quick queries.

Status: Work in progress — core features implemented and tested; a small GUI issue (Alfred handler) has been fixed and documentation scaffolding is being added.

---

## Work completed (summary)
- Implemented report generation (JSON/CSV/HTML), including **Top Subjects** section and overlay support.
- Added PDF viewer autodetection and Settings UI support (persisted to config file).
- Implemented virtualization prototype (VirtualThumbGrid and headless VirtualThumbGridModel) and extracted headless model for unit tests.
- Pre-rendered overlay generation for face matches (parallelized) and tests added.
- Created an Alfred assistant module (deterministic queries against DB): `case_agent.agent.alfred`.
- Added robust test fixes to handle headless or incomplete Tk installs (helper checks, skips when required).
- Added defensive registration for virtual grid on Tk root and class-level marker to avoid brittle tests.

## Key files changed/added
- case_agent/gui/virtual_grid.py — virtualization model + UI grid
- case_agent/gui/app.py — GUI skeleton and Settings dialog; added defensive Alfred handler
- case_agent/agent/alfred.py — Alfred query parsing and DB-backed file listing
- case_agent/utils/viewers.py — PDF viewer autodetection
- case_agent/reports.py — Top subjects and overlay pre-render logic
- tests/* — unit tests for viewer detection, overlays, virtualization model, and GUI smoke tests

## Database schema (models)
The canonical SQLAlchemy models are in `case_agent/db/models.py`. Key tables and fields (exact names):

- EvidenceFile: id, path, size, mtime, sha256, processed, file_metadata
- ExtractedText: id, file_id, page, text, provenance
- Entity: id, file_id, entity_type, text, span, provenance, confidence
- Event: id, description, timestamp, provenance
- Transcription: id, file_id, text, segments, provenance, created_at
- FaceMatch: id, source, probe_bbox, subject, gallery_path, distance, created_at

See `docs/DIAGRAMS/er_model.md` for the ER diagram and relations.

## Requirements (explicit & inferred)
- Python 3.11+ (project may run on newer versions; tests use local env)
- Windows-friendly GUI: Tk/Tcl installed (some CI runs are headless and tests will skip GUI parts)
- Dependencies: see `requirements.txt` (Playwright, Pillow, PyMuPDF, face recognition libs, etc.)
- Data & paths: repository expects a local SQLite DB (default: `C:/Projects/FileAnalyzer/file_analyzer.db`) and `reports/` directory for outputs

## Tests & CI
- Unit tests use pytest. Many GUI tests are marked to skip if Tk or PhotoImage support isn't available.
- Current local test results: most unit tests pass; there is 1 skipped GUI test in headless environments.

## Known issues / Remaining work
- GUI: improved layout and behavior: added defensive callbacks, an Alfred handler, top-subjects panel toggling (View menu), and cleaned Settings dialog; additional UX polish may follow.
- Virtualization UI polish: placeholder/spinner visuals, concurrency tuning and user controls (Settings UI already holds concurrency value).
- Document & annotate: add docstrings and inline comments across the codebase (non-functional changes only). Initial audit completed and module docstrings added for missing modules; remaining minor modules will be covered in a follow-up pass.
- Docs: add full docs (README, ARCHITECTURE, DIAGRAMS, CONTRIBUTING, TESTING, SECURITY, OPERATIONS) — scaffolding added.
- CI: ensure CI environment supports GUI tests or mark/skip appropriately; add matrix for headless vs GUI-enabled runs.
- Performance: run large dataset profiling, tune thumbnail generation concurrency and pre-rendered overlays.

## How to reproduce locally (developer quickstart)
1. Clone repository and create virtualenv
   - python -m venv .venv
   - .\.venv\Scripts\Activate.ps1 (PowerShell)
   - pip install -r requirements.txt
2. (Optional) install Playwright browsers: `python -m playwright install`
3. Run unit tests: `pytest -q`
4. Run GUI (if Tk installed): `python -c "from case_agent.gui.app import run_gui; run_gui()"`
5. Run a small dataset scan: `python scripts/run_full_scan.py --root <DATA_ROOT> --gallery <GALLERY> --out reports --limit 10`

## Next recommended steps (priority order)
1. Finish virtualization UI polish (spinner, placeholder, UX) and add integration tests that run only where Tk image support is available.
2. Complete docstring audit and add module-level docs for core modules. (Initial pass complete; follow-up to add more detailed function-level docs where helpful.)
3. GUI polish: spinner placeholders, layout improvements, View menu toggle for top subjects (in progress; minor UX updates completed).
3. Add CI jobs for headless and GUI-enabled environments; configure test matrix and Windows GUI runners (or use a remote runner with GUI support).
4. Add performance benchmarks and profiling script for full dataset runs.
5. Finalize developer docs and adopt pre-commit hooks.

---

For details and a permanent reference, see `docs/` and `docs/MISSION.md`.
