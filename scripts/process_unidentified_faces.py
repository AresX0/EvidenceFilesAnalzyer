"""Collect unidentified face crops (FaceMatch rows with no subject) into Images/unidentified.

Usage:
  python scripts/process_unidentified_faces.py --db ./file_analyzer.db --out Images/unidentified

The script will copy source image files into the output dir (creating it) and print a small summary.
"""
from pathlib import Path
import shutil
import argparse

from case_agent.db.init_db import init_db, get_session
from case_agent.db.models import FaceMatch


def run(db_path: str | Path, out_dir: str | Path):
    init_db(db_path)
    session = get_session()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = session.query(FaceMatch).filter(FaceMatch.subject == None).all()
    copied = 0
    for r in rows:
        src = Path(r.source)
        if not src.exists():
            continue
        dst = out_dir / src.name
        # avoid overwriting
        if dst.exists():
            continue
        try:
            shutil.copy2(src, dst)
            copied += 1
        except Exception:
            continue
    print(f"Copied {copied} unidentified face crops to {out_dir}")


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--db', default='./file_analyzer.db')
    p.add_argument('--out', default='Images/unidentified')
    args = p.parse_args()
    run(args.db, args.out)
