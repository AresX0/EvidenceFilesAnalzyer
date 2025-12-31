"""Command-line utilities for the case agent package.

Subcommands:
  export  - generate an extended audit report and write to JSON/CSV/HTML

Usage examples:
  python -m case_agent.cli export --db ./epstein.db --out ./epstein_report.json --format json
  python -m case_agent.cli export --db ./epstein.db --out ./epstein_report.csv --format csv
  python -m case_agent.cli export --db ./epstein.db --out ./epstein_report.html --format html
"""
from pathlib import Path
import argparse
import sys

from .reports import generate_extended_report, write_report_json, write_report_csv, write_report_html


def _filter_report(report: dict, entity_type: str = None, start: str = None, end: str = None, issues_only: bool = False) -> dict:
    # Work on a shallow copy to avoid mutating caller
    r = dict(report)
    if issues_only:
        return {"issues": r.get('issues', {}), "counts": r.get('counts', {})}

    if entity_type:
        # filter top_entities and sample_entities
        r['top_entities'] = [e for e in r.get('top_entities', []) if e.get('type') == entity_type]
        r['sample_entities'] = [e for e in r.get('sample_entities', []) if e.get('type') == entity_type]
        # adjust type counts
        if 'entity_type_counts' in r:
            r['entity_type_counts'] = {k: v for k, v in r['entity_type_counts'].items() if k == entity_type}

    if start or end:
        import dateutil.parser
        def in_range(ts):
            try:
                t = dateutil.parser.parse(ts)
            except Exception:
                return False
            if start:
                if t < dateutil.parser.parse(start):
                    return False
            if end:
                if t > dateutil.parser.parse(end):
                    return False
            return True
        r['events'] = [ev for ev in r.get('events', []) if in_range(ev.get('timestamp'))]
        # update timeline summary
        if r.get('events'):
            r['timeline_summary'] = {'earliest': r['events'][0].get('timestamp'), 'latest': r['events'][-1].get('timestamp')}
        else:
            r['timeline_summary'] = {}
    return r


def cmd_export(args):
    db = Path(args.db).resolve()
    out = Path(args.out).resolve()
    fmt = args.format.lower()
    report = generate_extended_report(db)

    # Apply filters if any
    report = _filter_report(report, entity_type=getattr(args, 'filter_entity_type', None), start=getattr(args, 'date_start', None), end=getattr(args, 'date_end', None), issues_only=getattr(args, 'issues_only', False))

    if fmt == 'json':
        write_report_json(report, out)
        print(f'Wrote JSON report to {out}')
    elif fmt == 'csv':
        write_report_csv(report, out)
        print(f'Wrote CSV report to {out}')
    elif fmt == 'html':
        write_report_html(report, out)
        print(f'Wrote HTML report to {out}')
    else:
        raise SystemExit('Unknown format: choose json|csv|html')


def main(argv=None):
    parser = argparse.ArgumentParser(prog='case_agent.cli')
    sub = parser.add_subparsers(dest='cmd')

    p_export = sub.add_parser('export', help='Export an audit report from the DB')
    p_export.add_argument('--db', required=True, help='Path to SQLite DB')
    p_export.add_argument('--out', required=True, help='Output path for report')
    p_export.add_argument('--format', choices=['json', 'csv', 'html'], default='json')
    p_export.add_argument('--filter-entity-type', help='Only include entities of this type (e.g., PERSON, ORG)')
    p_export.add_argument('--date-start', help='Start date (ISO) for events to include in timeline')
    p_export.add_argument('--date-end', help='End date (ISO) for events to include in timeline')
    p_export.add_argument('--issues-only', action='store_true', help='Export only issues summary')
    p_export.set_defaults(func=cmd_export)

    p_fixpdf = sub.add_parser('reprocess-pdfs', help='Re-run PDF extraction for PDFs with no text in DB')
    p_fixpdf.add_argument('--db', required=True, help='Path to SQLite DB')
    p_fixpdf.set_defaults(func=lambda args: __import__('case_agent.pipelines.text_extract', fromlist=['reprocess_pdfs_without_text']).reprocess_pdfs_without_text(db_path=args.db))

    p_face = sub.add_parser('face-search', help='Search for faces in an image or video against a local gallery')
    p_face.add_argument('--path', required=True, help='Path to image or video to search')
    p_face.add_argument('--gallery', required=True, help='Directory containing public gallery images')
    p_face.add_argument('--labeled', action='store_true', help='Treat --gallery as a labeled gallery where subfolders are subject names')
    p_face.add_argument('--out', help='Output JSON file (if omitted, prints JSON)')
    p_face.add_argument('--threshold', type=float, default=0.6, help='Distance threshold for face match (lower is stricter)')
    p_face.add_argument('--top-k', type=int, default=5, help='Return top K matches per face')
    p_face.add_argument('--interval', type=float, default=5.0, help='Frame sampling interval (s) for videos')
    p_face.add_argument('--persist-db', help='Path to SQLite DB to persist matches into (optional)')
    p_face.set_defaults(func=lambda args: __import__('case_agent.pipelines.face_search', fromlist=['cli_run']).cli_run(args))

    parsed = parser.parse_args(argv)
    if hasattr(parsed, 'func'):
        parsed.func(parsed)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
