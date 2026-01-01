# Compatibility shim: delegate media processing to case_agent implementation
from pathlib import Path
from case_agent.pipelines.media_extract import process_media
from case_agent.db.init_db import init_db, get_session
from case_agent.db.models import EvidenceFile
from config import DB_PATH, OUTPUT_DIR

def run():
    init_db(DB_PATH)
    session = get_session()
    files = session.query(EvidenceFile).all()
    for f in files:
        p = Path(f.path)
        if p.suffix.lower() in {".mp4", ".mov", ".mkv", ".avi"}:
            process_media(p, Path(OUTPUT_DIR), db_path=DB_PATH)

if __name__ == "__main__":
    run()
