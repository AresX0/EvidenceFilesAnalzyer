"""Walk a directory, compute SHA256 for files, and store inventory in the DB."""
import hashlib
import os
from pathlib import Path
import logging
from ..db.init_db import get_session, init_db
from ..db.models import EvidenceFile
from ..config import CHUNK_SIZE
import datetime

logger = logging.getLogger("case_agent.hash_inventory")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def walk_and_hash(evidence_dir: Path, db_path=None, commit=True):
    """Walk the evidence directory, compute SHA256, and upsert into DB.
    Returns a list of dicts with file info.
    """
    init_db(db_path) if db_path is not None else init_db()
    session = get_session()
    files = []
    for root, dirs, filenames in os.walk(evidence_dir):
        for fn in filenames:
            p = Path(root) / fn
            try:
                stat = p.stat()
            except OSError as e:
                logger.warning("Skipping %s: %s", p, e)
                continue
            sha = sha256_file(p)
            file_row = session.query(EvidenceFile).filter_by(sha256=sha).first()
            if not file_row:
                file_row = EvidenceFile(
                    path=str(p),
                    size=stat.st_size,
                    mtime=datetime.datetime.fromtimestamp(stat.st_mtime),
                    sha256=sha,
                    processed=False,
                )
                session.add(file_row)
                logger.info("Added %s", p)
            else:
                # Update metadata if changed
                updated = False
                if file_row.size != stat.st_size:
                    file_row.size = stat.st_size
                    updated = True
                mtime_dt = datetime.datetime.fromtimestamp(stat.st_mtime)
                if file_row.mtime != mtime_dt:
                    file_row.mtime = mtime_dt
                    updated = True
                if updated:
                    logger.info("Updated metadata for %s", p)
            files.append({"path": str(p), "sha256": sha})
    if commit:
        session.commit()
    return files


if __name__ == "__main__":
    import argparse
    from ..config import DEFAULT_EVIDENCE_DIR

    parser = argparse.ArgumentParser(description="Inventory evidence and compute SHA256 hashes")
    parser.add_argument("evidence_dir", nargs="?", default=str(DEFAULT_EVIDENCE_DIR))
    args = parser.parse_args()
    print("Scanning:", args.evidence_dir)
    result = walk_and_hash(Path(args.evidence_dir))
    print(f"Discovered {len(result)} files")
