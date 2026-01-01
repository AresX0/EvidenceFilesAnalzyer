import sqlite3, os

db = r'C:\Projects\FileAnalyzer\file_analyzer.db'
print('db_exists', os.path.exists(db))
if not os.path.exists(db):
    raise SystemExit('DB not found')
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print('tables:', tables)
if 'face_matches' in tables:
    cur.execute("SELECT COUNT(*) FROM face_matches")
    print('face_matches_rows:', cur.fetchone()[0])
    cur.execute("SELECT subject, COUNT(*) as c FROM face_matches GROUP BY subject ORDER BY c DESC LIMIT 20")
    rows = cur.fetchall()
    print('top_subjects:')
    for r in rows:
        print(' ', r)
else:
    print('face_matches table not found')
conn.close()