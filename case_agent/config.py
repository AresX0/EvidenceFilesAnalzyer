import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EVIDENCE_DIR = Path.cwd() / "evidence"
DEFAULT_DB_PATH = Path.cwd() / "file_analyzer.db"

# Limits and options
CHUNK_SIZE = 8192

# FFmpeg and OCR config
# Use explicit paths for determinism when installers are available
FFMPEG_PATH = r"C:\Path\ffmpeg.exe"
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"  # For OCR fallback (full path)

# Local LLM (Ollama) settings (not used by core pipelines)
OLLAMA_HOST = "http://localhost:11434"  # only used if local Ollama is configured

# Ensure evidence dir exists (but remains read-only by policy)
os.makedirs(DEFAULT_EVIDENCE_DIR, exist_ok=True)
