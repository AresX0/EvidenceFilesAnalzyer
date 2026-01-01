"""Anonymize listed persons in the DB by replacing their names with a generic Minor_N label.

Usage:
  python scripts/anonymize_persons.py --db ./file_analyzer.db --names "John Doe" "Jane Doe"

This will update Entity.text and FaceMatch.subject for exact matches and persist a mapping in anonymized_persons.json.
"""
from pathlib import Path
import json
import argparse

from case_agent.db.init_db import init_db, get_session
from case_agent.db.models import FaceMatch, Entity


def run(db_path: str | Path, names: list[str]):
    init_db(db_path)
    session = get_session()
    mapping = {}
    idx = 1
    for name in names:
        label = f"Minor_{idx}"
        mapping[name] = label
        # Update Entities
        ents = session.query(Entity).filter(Entity.entity_type == 'PERSON', Entity.text == name).all()
        for e in ents:
            e.text = label
        # Update FaceMatch
        fms = session.query(FaceMatch).filter(FaceMatch.subject == name).all()
        for f in fms:
            f.subject = label
        idx += 1
    session.commit()
    out = Path('anonymized_persons.json')
    d = {}
    if out.exists():
        d = json.loads(out.read_text())
    d.update(mapping)
    out.write_text(json.dumps(d, indent=2))
    print(f"Anonymized {len(mapping)} names; mapping written to {out}")


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--db', default='./file_analyzer.db')
    p.add_argument('--names', nargs='+', required=True)
    args = p.parse_args()
    run(args.db, args.names)
