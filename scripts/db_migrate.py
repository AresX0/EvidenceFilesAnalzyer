"""Simple migration helper for ad-hoc SQLite schema updates used by the project.

Currently supports:
 - add 'confidence' column to 'entities' table if missing
"""
import sqlite3
from pathlib import Path
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--db', required=True)
args = parser.parse_args()

db = Path(args.db)
conn = sqlite3.connect(str(db))
cur = conn.cursor()
# Check entities columns
cur.execute("PRAGMA table_info('entities')")
cols = [r[1] for r in cur.fetchall()]
if 'confidence' not in cols:
    print('Adding column confidence to entities')
    cur.execute("ALTER TABLE entities ADD COLUMN confidence TEXT DEFAULT 'low'")
    conn.commit()
else:
    print('column confidence already present')

conn.close()
print('Migration complete')