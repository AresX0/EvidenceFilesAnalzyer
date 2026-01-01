from pathlib import Path

BASE_DIR = Path("C:/case_agent")

EVIDENCE_DIR = BASE_DIR / "evidence"
OUTPUT_DIR = BASE_DIR / "output"

DB_PATH = BASE_DIR / "db" / "case.db"

WHISPER_MODEL = "medium"
FRAME_INTERVAL_SECONDS = 3

VECTOR_DIM = 768
