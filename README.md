EvidenceFilesAnalyzer
=====================

Overview
--------
EvidenceFilesAnalyzer is a local, offline, auditable case analysis toolkit designed to inventory files, extract and normalize text, perform entity extraction and timeline construction, and run media (audio/video/image) analysis including face detection and matching against labeled galleries.

Key features
------------
- File inventory and hashing with provenance (sha256).
- Text extraction from PDFs, DOCX, and images (OCR fallback).
- Entity extraction (spaCy) with chunked processing for large documents.
- Timeline builder and event extraction.
- Media processing: audio extraction & transcription (Whisper optional), video/image face detection.
- Face detection + matching (face_recognition/dlib if available; OpenCV Haar + facenet-pytorch fallback).
- Auditable SQLite database (`file_analyzer.db`) with SQLAlchemy models and exportable reports (JSON, CSV, HTML).
- CLI tools and a GUI skeleton to inspect results and export reports.

Security & privacy
------------------
This project is intended to be run locally and offline. **Do not commit or upload any sensitive or evidentiary files to remote repositories.** The codebase and packaging files may be pushed to GitHub, but evidence datasets must stay local.

Prerequisites (summary)
-----------------------
- OS: Windows 10/11 or Linux.
- Python 3.11 (recommended) — some native libraries have limited support for newer Python releases.
- Optional system tools for best performance:
  - CMake on PATH (needed to build `dlib` if you want `face_recognition` support)
  - Visual Studio Build Tools (Desktop C++ workload) on Windows to compile dlib
  - FFmpeg for audio/video handling
  - Tesseract-OCR (if relying on system OCR rather than pytesseract wheels)
- Recommended: Create a Python virtual environment for the project.

Getting started — Windows (novice-friendly)
--------------------------------------------
1. Install Python 3.11 from https://www.python.org/ (choose Add Python to PATH during installer).
2. Install Git: https://git-scm.com/downloads
3. Install required system packages (recommended):
   - FFmpeg: https://ffmpeg.org/download.html
   - Optional (for dlib): Download and install CMake from https://cmake.org/download/ and Visual Studio Build Tools (Desktop C++ workload) from https://visualstudio.microsoft.com/downloads/ (Build Tools).
4. Clone the repository:
   - git clone https://github.com/AresX0/EvidenceFilesAnalzyer.git
   - cd EvidenceFilesAnalzyer
5. Create and activate a virtual environment (PowerShell example):
   - python -m venv .venv
   - .\.venv\Scripts\Activate.ps1
6. Install Python dependencies:
   - python -m pip install --upgrade pip setuptools wheel
   - python -m pip install -r requirements.txt
7. Optional (if you want dlib/face_recognition):
   - Ensure CMake and Visual C++ Build Tools are available on PATH then run:
     - python -m pip install dlib
     - python -m pip install face_recognition
   - If building fails, either use a prebuilt wheel or use the OpenCV + facenet-pytorch fallback (included).
8. Install Playwright browsers if you run the scraper UI:
   - python -m pip install playwright
   - python -m playwright install

Quick usage
-----------
- Run the inventory and extraction pipeline (example):
  - python scripts/smoke_run.py --data "C:\path\to\evidence" --db file_analyzer.db
- Face-search example:
  - python -m case_agent.cli face-search --path C:\path\to\probe.jpg --gallery C:\path\to\gallery --labeled --out report.json --persist-db file_analyzer.db
- Persist all face crops against labeled gallery (aggregated best matches):
  - python scripts/persist_all_face_matches.py --faces C:\path\to\faces --gallery C:\path\to\Images --labeled --db file_analyzer.db --aggregate --threshold 0.9
- Export reports:
  - python -m case_agent.cli export --db file_analyzer.db --out reports/epstein_face_report.json --format json

Testing
-------
- Run unit tests:
  - python -m pip install pytest
  - pytest -q

Developer notes
---------------
- The DB models are in `case_agent/db/models.py` (SQLAlchemy). Migration is not automated; keep schema changes minimal.
- Face matching pipeline is in `case_agent/pipelines/face_search.py`. It prefers `face_recognition` when available and falls back to OpenCV + facenet-pytorch.
- Many scripts live under `scripts/` for data processing, tuning, and maintenance.

Contributing
------------
- Please open issues or PRs on the GitHub repo. For sensitive tests or sample data, include only synthetic or public-domain data in tests and examples.

License & Attribution
---------------------
See LICENSE file for license terms. External dependencies have their own licenses (see `requirements.txt`).

Support
-------
If you want me to upload this repo to your GitHub, provide a Personal Access Token (PAT) with `repo` scope (do NOT include any evidence data); or instruct me to create a branch or PR and you can push it manually.

