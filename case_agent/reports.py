"""Extended audit report generation utilities."""
from pathlib import Path
from typing import Dict, Any, List
from .db.init_db import init_db, get_session
from .db.models import EvidenceFile, ExtractedText, Entity, Event, Transcription
import json


def generate_extended_report(db_path: str | Path, excerpt_chars: int = 200, max_entities: int = 50) -> Dict[str, Any]:
    """Build an extended, auditable report from the DB.

    Includes:
      - counts and file list
      - top entities by type and frequency
      - sample entities
      - excerpts of extracted text and transcriptions
      - events and timeline summary (earliest/latest)
      - basic issues (files with no extracted text, PDFs without text, media without transcription)
    """
    init_db(db_path)
    session = get_session()

    files = [
        {"id": f.id, "path": f.path, "sha256": f.sha256, "size": f.size, "mime": getattr(f, 'mime', None)} for f in session.query(EvidenceFile).all()
    ]

    counts = {
        "files": session.query(EvidenceFile).count(),
        "extracted_text": session.query(ExtractedText).count(),
        "entities": session.query(Entity).count(),
        "events": session.query(Event).count(),
        "transcriptions": session.query(Transcription).count(),
    }

    # entity aggregates
    from sqlalchemy import func
    entity_counts = (
        session.query(Entity.entity_type, Entity.text, func.count(Entity.id).label('n'))
        .group_by(Entity.entity_type, Entity.text)
        .order_by(func.count(Entity.id).desc())
        .limit(max_entities)
        .all()
    )
    top_entities = []
    for etype, text, n in entity_counts:
        top_entities.append({"type": etype, "text": text, "count": int(n)})

    # counts by entity type
    type_counts = {row[0]: int(row[1]) for row in session.query(Entity.entity_type, func.count(Entity.id)).group_by(Entity.entity_type).all()}

    # sample entities
    sample_entities = []
    for e in session.query(Entity).limit(max_entities).all():
        sample_entities.append({"type": e.entity_type, "text": e.text, "confidence": getattr(e, 'confidence', 'low'), "provenance": e.provenance})

    # text excerpts per file (first 3 excerpts per file)
    excerpts = {}
    for et in session.query(ExtractedText).limit(2000).all():
        key = et.provenance.get('sha256') if isinstance(et.provenance, dict) else None
        if key is None:
            key = getattr(et, 'file_id', None)
        if key not in excerpts:
            excerpts[key] = []
        txt = (et.text or '')
        if len(excerpts[key]) < 3:
            excerpts[key].append({"page": et.page, "excerpt": txt[:excerpt_chars]})

    # transcription excerpts
    trans_excerpts = []
    for t in session.query(Transcription).limit(500).all():
        file_row = session.query(EvidenceFile).filter_by(id=t.file_id).first()
        trans_excerpts.append({"id": t.id, "file_id": t.file_id, "file_sha256": getattr(file_row, 'sha256', None), "text_excerpt": (t.text or '')[:excerpt_chars], "provenance": t.provenance})

    # events
    events = []
    for ev in session.query(Event).order_by(Event.timestamp).limit(1000).all():
        events.append({"id": ev.id, "description": ev.description, "timestamp": ev.timestamp.isoformat() if hasattr(ev.timestamp, 'isoformat') else ev.timestamp, "provenance": ev.provenance})

    timeline_summary = {}
    first = session.query(Event).order_by(Event.timestamp).first()
    last = session.query(Event).order_by(Event.timestamp.desc()).first()
    if first:
        timeline_summary['earliest'] = getattr(first, 'timestamp', None)
    if last:
        timeline_summary['latest'] = getattr(last, 'timestamp', None)

    # issues: files with no extracted text
    file_text_counts = {f.id: session.query(ExtractedText).filter_by(file_id=f.id).count() for f in session.query(EvidenceFile).all()}
    files_no_text = [ {"id": fid, "path": next((f['path'] for f in files if f['id']==fid), None)} for fid, c in file_text_counts.items() if c == 0 ]

    # PDFs with no text (helpful to detect missing PDF extractor)
    pdfs_no_text = []
    for f in session.query(EvidenceFile).filter(EvidenceFile.path.ilike('%.pdf')):
        if session.query(ExtractedText).filter_by(file_id=f.id).count() == 0:
            pdfs_no_text.append({"id": f.id, "path": f.path, "sha256": f.sha256})

    # media files without transcriptions
    media_no_trans = []
    media_suffixes = {'.wav', '.mp3', '.mp4', '.m4a', '.mov', '.avi', '.mkv'}
    for f in session.query(EvidenceFile).all():
        if Path(f.path).suffix.lower() in media_suffixes:
            if session.query(Transcription).filter_by(file_id=f.id).count() == 0:
                media_no_trans.append({"id": f.id, "path": f.path, "sha256": f.sha256})

    issues = {
        "files_no_text": files_no_text,
        "pdfs_no_text": pdfs_no_text,
        "media_no_transcription": media_no_trans,
    }

    # Compute person co-occurrence and location presence
    from collections import Counter, defaultdict
    person_presence = {}

    # Group entities by document page (use provenance sha256 & page when available)
    groups = defaultdict(lambda: {"persons": [], "gpes": []})
    for e in session.query(Entity).all():
        prov = e.provenance or {}
        sha = None
        page = None
        if isinstance(prov, dict):
            sha = prov.get('sha256')
            page = prov.get('page')
        key = (sha, page)
        if e.entity_type == 'PERSON':
            groups[key]['persons'].append(e.text)
        if e.entity_type in {'GPE', 'LOC'}:
            groups[key]['gpes'].append(e.text)

    co_counts = defaultdict(lambda: {'co_mentions': Counter(), 'locations': Counter()})
    for (sha, page), vals in groups.items():
        persons = list(set(vals['persons']))
        gpes = list(set(vals['gpes']))
        for p in persons:
            for other in persons:
                if other == p:
                    continue
                co_counts[p]['co_mentions'][other] += 1
            for g in gpes:
                co_counts[p]['locations'][g] += 1

    person_presence = []
    for p, data in co_counts.items():
        person_presence.append({
            'person': p,
            'top_co_mentions': [{ 'person': k, 'count': v } for k, v in data['co_mentions'].most_common(5)],
            'top_locations': [{ 'location': k, 'count': v } for k, v in data['locations'].most_common(5)],
        })

    # Include face matches via SQLAlchemy model if available
    face_matches = []
    try:
        from .db.models import FaceMatch
        # Ensure DB initialized
        init_db(db_path)
        session = get_session()
        for fm in session.query(FaceMatch).order_by(FaceMatch.created_at.desc()).limit(1000).all():
            face_matches.append({'source': fm.source, 'probe_bbox': fm.probe_bbox, 'subject': fm.subject, 'gallery_path': fm.gallery_path, 'distance': fm.distance, 'created_at': fm.created_at})
    except Exception:
        # Non-fatal: report without face matches
        pass

    report = {
        "files": files,
        "counts": counts,
        "entity_type_counts": type_counts,
        "top_entities": top_entities,
        "sample_entities": sample_entities,
        "excerpts": excerpts,
        "transcriptions": trans_excerpts,
        "events": events,
        "timeline_summary": timeline_summary,
        "issues": issues,
        "person_presence": person_presence,
        "face_matches": face_matches,
    }
    return report


def write_report_json(report: Dict[str, Any], path: str | Path):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w', encoding='utf-8') as fh:
        json.dump(report, fh, indent=2)


def write_report_csv(report: Dict[str, Any], path: str | Path):
    # Basic CSV of files and counts; keep simple and auditable
    import csv
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['file_path', 'sha256', 'size'])
        for f in report.get('files', []):
            w.writerow([f.get('path'), f.get('sha256'), f.get('size')])
        # write counts as rows
        w.writerow([])
        w.writerow(['metric', 'value'])
        for k, v in report.get('counts', {}).items():
            w.writerow([k, v])
        # write top entity table
        w.writerow([])
        w.writerow(['entity_type', 'text', 'count'])
        for e in report.get('top_entities', []):
            w.writerow([e.get('type'), e.get('text'), e.get('count')])
        # write issues summaries (counts)
        w.writerow([])
        w.writerow(['issue', 'count'])
        issues = report.get('issues', {})
        w.writerow(['files_no_text', len(issues.get('files_no_text', []))])
        w.writerow(['pdfs_no_text', len(issues.get('pdfs_no_text', []))])
        w.writerow(['media_no_transcription', len(issues.get('media_no_transcription', []))])


def write_report_html(report: Dict[str, Any], path: str | Path):
    """Create a simple HTML summary report for quick viewing."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w', encoding='utf-8') as fh:
        fh.write('<html><head><meta charset="utf-8"><title>Audit Report</title></head><body>')
        fh.write('<h1>Audit Report</h1>')
        fh.write('<h2>Counts</h2>')
        fh.write('<ul>')
        for k, v in report.get('counts', {}).items():
            fh.write(f'<li><strong>{k}</strong>: {v}</li>')
        fh.write('</ul>')

        fh.write('<h2>Top Entities</h2>')
        fh.write('<table border="1"><tr><th>Type</th><th>Text</th><th>Count</th></tr>')
        for e in report.get('top_entities', []):
            fh.write(f"<tr><td>{e.get('type')}</td><td>{e.get('text')}</td><td>{e.get('count')}</td></tr>")
        fh.write('</table>')

        fh.write('<h2>Timeline Summary</h2>')
        ts = report.get('timeline_summary', {})
        fh.write('<ul>')
        fh.write(f"<li>Earliest: {ts.get('earliest')}</li>")
        fh.write(f"<li>Latest: {ts.get('latest')}</li>")
        fh.write('</ul>')

        fh.write('<h2>Issues</h2>')
        issues = report.get('issues', {})
        fh.write('<ul>')
        fh.write(f"<li>Files with no text: {len(issues.get('files_no_text', []))}</li>")
        fh.write(f"<li>PDFs with no text: {len(issues.get('pdfs_no_text', []))}</li>")
        fh.write(f"<li>Media without transcription: {len(issues.get('media_no_transcription', []))}</li>")
        fh.write('</ul>')

        fh.write('</body></html>')

