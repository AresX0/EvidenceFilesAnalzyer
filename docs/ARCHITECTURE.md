# Architecture — FileAnalyzer

## System context
FileAnalyzer is structured around a small set of responsibilities:
- Ingest: traverse file systems and create a canonical inventory (hashes, metadata)
- Parse & Extract: extract text, OCR, PDF page images, audio/video frames
- Analyze: perform entity extraction, face detection, face matching
- Persist & Query: store results in a local SQLite DB (models: EvidenceFile, FaceMatch, Entity)
- Report & UI: export reports (JSON/CSV/HTML) and provide a GUI for exploration

## Component breakdown
- case_agent.pipelines — extraction and analysis pipelines (hash_inventory, text_extract, media_extract, face_search)
- case_agent.db — DB initialization and models
- case_agent.reports — report generation logic and overlay rendering
- case_agent.gui — small Tk GUI (people explorer) and virtualization
- case_agent.agent — deterministic assistant (Alfred) to query DB
- scripts/ — convenience scripts (run_full_scan.py, pdf_face_detect.py)

## Data flows
1. walk_and_hash discovers files and persists metadata to DB
2. Pipelines run per-file: extract text, detect media, detect faces, compute embeddings
3. face_search compares probes to the labeled gallery and persists matches
4. Reporting aggregates DB results and writes JSON/CSV/HTML; overlays created per image

## Extension points
- Parsers & Analyzers: implement new parser or analyzer functions in `case_agent/pipelines/` and add tests
- Outputs: add new writer in `case_agent/reports` (e.g., Parquet or other formats)

## Deployment
- Local developer: venv + pip + optional Playwright browser install
- Container: containerization possible; ensure system packages for Tk and headless display handling if GUI tests are needed

## Observability & Resilience
- Logging: module-level loggers; encourage log rotation for long runs
- Retries: long-running IO should be retried externally or added locally (e.g., requests with backoff)
- Resource limits: thumbnail and overlay generation are parallelized; use `THUMB_RENDER_CONCURRENCY` to control concurrency

