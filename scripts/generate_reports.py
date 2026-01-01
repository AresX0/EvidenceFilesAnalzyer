from case_agent.reports import generate_extended_report, write_report_json, write_report_csv, write_report_html
from pathlib import Path

def main(db_path=r"C:\Projects\FileAnalyzer\file_analyzer.db", out_dir=r"C:\Projects\FileAnalyzer\reports"):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = generate_extended_report(db_path)
    write_report_json(report, out_dir / 'epstein_face_report.json')
    write_report_csv(report, out_dir / 'epstein_face_report.csv')
    write_report_html(report, out_dir / 'epstein_face_report.html')

    # Write people_summary.csv (person, file_count, files, top_matches)
    import csv, sqlite3
    people = report.get('people', [])
    db = db_path
    conn = sqlite3.connect(str(db))
    cur = conn.cursor()
    with open(out_dir / 'people_summary.csv', 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['person', 'file_count', 'files', 'top_matches'])
        for p in people:
            files = p.get('files', [])
            top_matches = []
            if files:
                placeholders = ','.join('?' for _ in files)
                q = f"SELECT subject, COUNT(*) as c FROM face_matches WHERE source IN ({placeholders}) GROUP BY subject ORDER BY c DESC LIMIT 5"
                cur.execute(q, files)
                top_matches = [f"{r[0]}:{r[1]}" for r in cur.fetchall() if r[0] is not None]
            w.writerow([p.get('person'), p.get('file_count'), ';'.join(files), ';'.join(top_matches)])
    conn.close()

    print('Wrote reports to', out_dir)

if __name__ == '__main__':
    main()