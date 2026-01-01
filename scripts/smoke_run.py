"""Create sample evidence, run the case agent pipeline end-to-end, and emit an audit report.

Usage:
    python scripts/smoke_run.py --evidence ./evidence --db ./file_analyzer.db --out ./audit_report.json

This is deterministic and fully local.
"""
import argparse
import json
from pathlib import Path
import hashlib
import wave
from PIL import Image, ImageDraw, ImageFont
import fitz

import sys
sys.path.insert(0, r'C:\Projects\FileAnalyzer')
from case_agent.db.init_db import init_db, get_session
from case_agent.pipelines.hash_inventory import walk_and_hash
from case_agent.pipelines.text_extract import extract_for_file
from case_agent.pipelines.entity_extract import extract_entities_for_file
from case_agent.pipelines.media_extract import process_media
from case_agent.pipelines.timeline_builder import build_timeline
from case_agent.db.models import EvidenceFile


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda: fh.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def create_samples(evidence_dir: Path):
    evidence_dir.mkdir(parents=True, exist_ok=True)
    # 1) text file
    t = evidence_dir / 'sample_note.txt'
    t.write_text('Alice visited Acme Corp on 2025-01-01. Follow up required.')

    # 2) pdf with text
    pdf_path = evidence_dir / 'sample_report.pdf'
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), 'Report: Meeting on 2025-11-11 with Bob Smith at Example Inc', fontsize=12)
    doc.save(str(pdf_path))

    # 3) image with text (for OCR)
    img_path = evidence_dir / 'sample_img.png'
    img = Image.new('RGB', (800, 200), color='white')
    d = ImageDraw.Draw(img)
    try:
        # Use a default font - system may not have fonts; PIL fallback will work
        f = ImageFont.load_default()
    except Exception:
        f = None
    d.text((10, 50), 'Jane Roe 2024-05-06', fill='black', font=f)
    img.save(img_path)

    # 4) audio WAV (silence or short frame)
    wav_path = evidence_dir / 'sample_audio.wav'
    with wave.open(str(wav_path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        # simple short silent waveform
        w.writeframes(b'\x00\x00' * 16000)

    # 5) docx
    try:
        import docx
        docx_path = evidence_dir / 'sample_doc.docx'
        docx.Document().add_paragraph('Factura dated 2025-03-03 regarding Acme Corporation.').save(str(docx_path))
    except Exception:
        pass

    return [t, pdf_path, img_path, wav_path]


def generate_report(db_path: Path):
    init_db(db_path)
    session = get_session()
    files = [
        {
            'path': f.path,
            'sha256': f.sha256,
            'size': f.size
        }
        for f in session.query(EvidenceFile).all()
    ]
    # counts
    from case_agent.db.models import ExtractedText, Entity, Event, Transcription
    counts = {
        'extracted_text': session.query(ExtractedText).count(),
        'entities': session.query(Entity).count(),
        'events': session.query(Event).count(),
        'transcriptions': session.query(Transcription).count(),
    }
    # sample entities
    sample_entities = [
        { 'type': e.entity_type, 'text': e.text, 'provenance': e.provenance } for e in session.query(Entity).limit(20).all()
    ]
    report = {
        'files': files,
        'counts': counts,
        'sample_entities': sample_entities,
    }
    return report


def run_pipeline(evidence_dir: Path, db_path: Path, out_dir: Path):
    init_db(db_path)
    # 1. Inventory
    walk_and_hash(evidence_dir, db_path=db_path)
    # 2. Extract text & entities
    for f in evidence_dir.iterdir():
        if f.is_file():
            extract_for_file(f, db_path=db_path)
            extract_entities_for_file(f, db_path=db_path)
            # media process
            if f.suffix.lower() in {'.mp4', '.mov', '.mkv', '.avi', '.wav'}:
                process_media(f, out_dir, db_path=db_path)
    # 3. Build timeline
    build_timeline(db_path=db_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', default='./evidence')
    parser.add_argument('--db', default='./file_analyzer.db')
    parser.add_argument('--out', default='./media_out')
    parser.add_argument('--report', default='./audit_report.json')
    args = parser.parse_args()

    evidence_dir = Path(args.evidence).resolve()
    db_path = Path(args.db).resolve()
    out_dir = Path(args.out).resolve()

    print('Creating sample evidence in', evidence_dir)
    create_samples(evidence_dir)

    print('Running pipeline...')
    run_pipeline(evidence_dir, db_path, out_dir)

    print('Generating report...')
    report = generate_report(db_path)
    with open(args.report, 'w', encoding='utf-8') as fh:
        json.dump(report, fh, indent=2)
    print('Saved audit report to', args.report)


if __name__ == '__main__':
    main()
