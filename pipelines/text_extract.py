# Compatibility shim: delegate text extraction to case_agent implementation
from pathlib import Path
from case_agent.pipelines.text_extract import extract_for_file
from case_agent.db.init_db import init_db, get_session
from case_agent.db.models import EvidenceFile
from config import DB_PATH

def run():
    init_db(DB_PATH)
    session = get_session()
    files = session.query(EvidenceFile).all()
    for f in files:
        extract_for_file(Path(f.path), db_path=DB_PATH)

if __name__ == "__main__":
    run()
