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

# PDF viewer (can be autodetected and persisted by GUI settings)
PDF_VIEWER = None

# Local LLM (Ollama) settings (not used by core pipelines)
OLLAMA_HOST = "http://localhost:11434"  # only used if local Ollama is configured

# Ensure evidence dir exists (but remains read-only by policy)
os.makedirs(DEFAULT_EVIDENCE_DIR, exist_ok=True)

# Persistence helpers for simple user-editable settings
import json
_CONFIG_PATH = Path(__file__).resolve().parent.parent / 'case_agent_config.json'

def _load_user_config():
    global PDF_VIEWER
    try:
        if _CONFIG_PATH.exists():
            j = json.loads(_CONFIG_PATH.read_text(encoding='utf-8'))
            PDF_VIEWER = j.get('PDF_VIEWER', PDF_VIEWER)
    except Exception:
        pass


def save_user_config():
    try:
        _CONFIG_PATH.write_text(json.dumps({'PDF_VIEWER': PDF_VIEWER}, indent=2), encoding='utf-8')
        return True
    except Exception:
        return False

# Load on import
_load_user_config()