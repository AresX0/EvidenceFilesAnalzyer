from case_agent.reports import generate_extended_report, write_report_json, write_report_csv, write_report_html
from pathlib import Path

def main(db_path=r"C:\Projects\FileAnalyzer\file_analyzer.db", out_dir=r"C:\Projects\FileAnalyzer\reports"):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = generate_extended_report(db_path)
    write_report_json(report, out_dir / 'epstein_face_report.json')
    write_report_csv(report, out_dir / 'epstein_face_report.csv')
    write_report_html(report, out_dir / 'epstein_face_report.html')
    print('Wrote reports to', out_dir)

if __name__ == '__main__':
    main()