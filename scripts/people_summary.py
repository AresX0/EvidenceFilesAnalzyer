import json, os, sqlite3
from pathlib import Path

REPORT = Path(r'C:/Projects/FileAnalyzer/reports/epstein_face_report.json')
OUT = Path(r'C:/Projects/FileAnalyzer/reports/people_summary.csv')

if not REPORT.exists():
    raise SystemExit('Report missing: ' + str(REPORT))

with REPORT.open('r', encoding='utf-8') as fh:
    rpt = json.load(fh)

people = rpt.get('people', [])

conn = sqlite3.connect(r'C:/Projects/FileAnalyzer/file_analyzer.db')
cur = conn.cursor()

rows = []
for p in people:
    person = p.get('person')
    files = p.get('files', [])
    file_placeholders = ','.join('?' for _ in files) if files else 'NULL'
    top_matches = []
    if files:
        q = f"SELECT subject, COUNT(*) as c FROM face_matches WHERE source IN ({file_placeholders}) GROUP BY subject ORDER BY c DESC LIMIT 5"
        cur.execute(q, files)
        top_matches = [f"{r[0]}:{r[1]}" for r in cur.fetchall() if r[0] is not None]
    rows.append({'person': person, 'file_count': len(files), 'files': ';'.join(files), 'top_matches': ';'.join(top_matches)})

conn.close()

import csv
OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open('w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh)
    w.writerow(['person', 'file_count', 'files', 'top_matches'])
    for r in rows:
        w.writerow([r['person'], r['file_count'], r['files'], r['top_matches']])

print('Wrote', OUT)
