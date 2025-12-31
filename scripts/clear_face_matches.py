"""Clear face_matches table in project DB (use with caution)."""
from case_agent.db.init_db import init_db, get_session
from case_agent.db.models import FaceMatch
import argparse

p = argparse.ArgumentParser()
p.add_argument('--db', help='DB path (defaults to project DB)', default=None)
args = p.parse_args()
init_db(args.db)
s = get_session()
removed = s.query(FaceMatch).delete()
s.commit()
print('Removed', removed, 'rows from face_matches')
