# Instructions to Run and Populate the DB (Developer Guide)

This file explains how to set up a developer environment, populate the SQLite database, run the face pipeline, and produce searchable reports and per-person pages.

## 1) Setup

- Create a Python 3.11+ virtual environment and install dependencies:

  - python -m venv .venv
  - .\.venv\Scripts\activate  (Windows PowerShell)
  - pip install -r requirements.txt
  - python -m pip install -r case_agent/requirements.txt  (if present)
  - Install any optional system deps:
    - FFmpeg (for media extraction) and ensure `FFMPEG_PATH` in `case_agent/config.py` is correct
    - Tesseract (optional OCR) if you expect to OCR images/PDFs

## 2) Inventory files (hashing)

- Add files to the DB inventory by running the hashing inventory:

  - python -m case_agent.pipelines.hash_inventory <evidence_dir> --db ./file_analyzer.db

  Example:
  - python -m case_agent.pipelines.hash_inventory "C:\path\to\evidence" --db C:\Projects\FileAnalyzer\file_analyzer.db

  This will populate the `EvidenceFile` table with path, sha256, size, mtime.

## 3) Extract text and entities

- For all files in the inventory, extract page-level text and persist to `ExtractedText`:

  - python -m case_agent.pipelines.text_extract <file(s)> --db ./file_analyzer.db

- Run deterministic NER on extracted text to populate `Entity` rows:

  - python -m case_agent.pipelines.entity_extract <file(s)> --db ./file_analyzer.db

- To re-run for all PDF files missing text, use the helper:

  - python -c "from case_agent.pipelines.text_extract import reprocess_pdfs_without_text; reprocess_pdfs_without_text('./file_analyzer.db')"

## 4) Process media (audio/video)

- For each video/audio, extract audio and persist `Transcription` rows (uses local whisper if installed):

  - python -m case_agent.pipelines.media_extract <video_or_audio_file> --out ./media_out --db ./file_analyzer.db

- The pipeline will automatically run entity extraction on transcriptions and add `Entity` rows so audio/video mentions are searchable.

## 5) Detect faces & match to labeled gallery

- Prepare a labeled gallery under `Images/` (subject folders containing example images).

- Run the full face pipeline which will:
  - Detect faces in PDFs, images and videos, write crops to `faces_out` and search a labeled gallery
  - Persist matches to `FaceMatch` table
  - Optionally aggregate results using `--aggregate`

  Example:
  - python scripts/run_full_scan.py --root "C:\path\to\evidence" --gallery "C:\Projects\FileAnalyzer\Images" --db C:\Projects\FileAnalyzer\file_analyzer.db --faces-out C:\Projects\FileAnalyzer\faces_full --out C:\Projects\FileAnalyzer\reports --aggregate --threshold 0.9

- To process any remaining unlabeled crops into `Images/unidentified`:

  - python scripts/process_unidentified_faces.py --db ./file_analyzer.db --out Images/unidentified

## 6) Generate reports

- Produce JSON/CSV/HTML reports:

  - python -m case_agent.cli export --db ./file_analyzer.db --out reports/epstein_face_report.json --format json
  - Or run scripts/run_full_scan.py which writes JSON/CSV/HTML into an `out` directory.

- The HTML includes:
  - Counts, issues, top entities
  - New sections showing people by media type (Text, Images, Video, Audio) with links to files
  - Per-person pages under `reports/people/` with thumbnails and overlaid faces when available

## 7) GUI

- To run the Tk GUI (if you have a GUI-capable environment):

  - python -m case_agent.gui

- The GUI uses the DB and the configured settings (persisted to `case_agent_config.json`). The Viewer autodetection and settings are under Settings.

## 8) Anonymize minors (manual step)

- If you need to anonymize known minors, use the helper script to replace their names with Generic labels (Minor_N):

  - python scripts/anonymize_persons.py --db ./file_analyzer.db --names "Firstname Lastname" "Another Name"

  This updates `Entity` and `FaceMatch` entries and writes a mapping to `anonymized_persons.json`.

## 9) How to find "Donald Trump" across all media

- Using the DB and scripts you can list files mentioning a person across categories. For a manual quick check in Python:

  from case_agent.db.init_db import init_db, get_session
  from case_agent.db.models import Entity, FaceMatch, EvidenceFile
  init_db('./file_analyzer.db')
  s = get_session()
  # text-based mentions
  ents = [ (e.text, EvidenceFile.query.filter_by(id=e.file_id).first().path) for e in s.query(Entity).filter(Entity.entity_type=='PERSON', Entity.text.ilike('%Donald Trump%')).all() ]
  # face matches
  fms = s.query(FaceMatch).filter(FaceMatch.subject.ilike('%Donald Trump%')).all()

## 10) Notes & best practices

- Do not commit generated reports, face crops, or DB files to git. The repo `.gitignore` is configured to ignore these artifacts.
- For reproducibility, run the inventory before text/media/face processing so file metadata and provenance are present in the DB.
- If you want to add external images to labeled galleries automatically, do so manually and vet the images for GDPR/privacy and minor handling.

---

If you want, I can also add a CLI helper that prints a per-person summary showing which files they appear in for each category (text, images, video, audio). Want me to add that? 
