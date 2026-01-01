"""Full dataset scan wrapper.

Performs:
 - inventory and basic extraction (text/entities/media)
 - PDF page rendering and face extraction
 - image face detection
 - video frame sampling and detection
 - matching against a labeled gallery (subject embeddings)
 - persist aggregated best matches into DB
 - export JSON/CSV/HTML reports to reports/ directory

Usage example (use forward slashes to avoid escape issues):
  python scripts/run_full_scan.py --root "C:/Users/doran/OneDrive - Say Family/legal analysis/Epstein" --gallery "C:/Projects/FileAnalyzer/Images" --db C:/Projects/FileAnalyzer/file_analyzer.db --out C:/Projects/FileAnalyzer/reports --limit 0
"""
from pathlib import Path
import argparse
import json
import os
import sys
import time

sys.path.insert(0, r'C:\Projects\FileAnalyzer')
from case_agent.db.init_db import init_db, get_session
from case_agent.pipelines.hash_inventory import walk_and_hash
from case_agent.pipelines.text_extract import extract_for_file
from case_agent.pipelines.entity_extract import extract_entities_for_file
from case_agent.pipelines.media_extract import process_media
from case_agent.pipelines import face_search
from case_agent.pipelines.face_search import search_labeled_gallery_for_image
from case_agent.reports import generate_extended_report, write_report_json, write_report_csv, write_report_html
from scripts.pdf_face_detect import process_pdf


def process_pdf_file(p: Path, faces_out: Path, gallery: Path, db_path: Path, aggregate=True, threshold=0.9, top_k=5):
    res = process_pdf(p, faces_out)
    # for each page, check crops
    for pg in res.get('pages', []):
        for f in pg.get('faces', []):
            crop = Path(f.get('crop'))
            if crop.exists():
                r = search_labeled_gallery_for_image(crop, gallery, threshold=threshold, top_k=top_k)
                face_search._persist_results(db_path or None, r, aggregate=aggregate)


def process_image_file(p: Path, faces_out: Path, gallery: Path, db_path: Path, aggregate=True, threshold=0.9, top_k=5):
    # detect faces and save crops if desired
    dets = face_search.find_faces_in_image(p)
    if not dets:
        # fallback: try to compute whole-image embedding and compare
        r = face_search.search_labeled_gallery_for_image(p, gallery, threshold=threshold, top_k=top_k)
        face_search._persist_results(db_path or None, r, aggregate=aggregate)
        return
    # If detections, optionally crop and persist per-crop
    try:
        from PIL import Image
        img = Image.open(p).convert('RGB')
    except Exception:
        img = None
    for i, d in enumerate(dets):
        bbox = d.get('bbox')
        if img is not None and bbox:
            left = bbox.get('left', 0)
            top = bbox.get('top', 0)
            right = bbox.get('right')
            bottom = bbox.get('bottom')
            crop = img.crop((left, top, right, bottom))
            crop_path = faces_out / f"{p.stem}_f{i+1}.jpg"
            faces_out.mkdir(parents=True, exist_ok=True)
            crop.save(crop_path)
            r = search_labeled_gallery_for_image(crop_path, gallery, threshold=threshold, top_k=top_k)
            face_search._persist_results(db_path or None, r, aggregate=aggregate)
        else:
            # if no crop, persist using whole-image method
            r = face_search.search_labeled_gallery_for_image(p, gallery, threshold=threshold, top_k=top_k)
            face_search._persist_results(db_path or None, r, aggregate=aggregate)


def process_video_file(p: Path, gallery: Path, db_path: Path, aggregate=True, threshold=0.9, top_k=5, interval=5.0):
    frames = face_search.find_faces_in_video(p, interval_seconds=interval)
    for frame in frames:
        ts = frame.get('timestamp')
        dets = frame.get('detections', [])
        for d in dets:
            # Each detection includes an embedding; we will compare to gallery image embeddings
            # Create a synthetic probe by writing frame crop if needed - here we rely on in-memory embedding
            enc = d.get('embedding')
            # Compare to gallery image-level embeddings
            gallery_embs = face_search._load_gallery_embeddings(gallery)
            best = []
            for gp, genc in gallery_embs.items():
                dist = face_search._compare_embedding(enc, genc)
                if dist <= threshold:
                    best.append({'path': gp, 'distance': float(dist)})
            if best:
                best.sort(key=lambda x: x['distance'])
                res = {'source': str(p), 'num_subjects': 1, 'subject_matches': [{'subject': None, 'best_distance': best[0]['distance'], 'matches': best[:top_k]}]}
                face_search._persist_results(db_path or None, res, aggregate=aggregate)


def run_full_scan(root: Path, gallery: Path, db_path: Path, faces_out: Path, out_dir: Path, aggregate=True, threshold=0.9, top_k=5, limit=0):
    start = time.time()
    init_db(db_path)
    # 1) inventory
    print('Walking & hashing files...')
    walk_and_hash(root, db_path=db_path)

    # iterate through files
    count = 0
    for p in root.rglob('*'):
        if limit and limit > 0 and count >= limit:
            break
        if not p.is_file():
            continue
        count += 1
        ext = p.suffix.lower()
        try:
            print('Processing', p)
            # Extract text & entities
            extract_for_file(p, db_path=db_path)
            extract_entities_for_file(p, db_path=db_path)
            if ext in {'.mp4', '.mov', '.mkv', '.avi'}:
                process_video_file(p, gallery, db_path, aggregate=aggregate, threshold=threshold, top_k=top_k)
            elif ext in {'.pdf'}:
                process_pdf_file(p, faces_out, gallery, db_path, aggregate=aggregate, threshold=threshold, top_k=top_k)
            elif ext in {'.jpg', '.jpeg', '.png'}:
                process_image_file(p, faces_out, gallery, db_path, aggregate=aggregate, threshold=threshold, top_k=top_k)
            elif ext in {'.wav', '.mp3'}:
                process_media(p, out_dir, db_path=db_path)
        except Exception as e:
            print('Error processing', p, e)

    # Build timeline
    from case_agent.pipelines.timeline_builder import build_timeline
    print('Building timeline...')
    build_timeline(db_path=db_path)

    # Generate report
    out_dir.mkdir(parents=True, exist_ok=True)
    report = generate_extended_report(db_path)
    json_path = out_dir / 'epstein_face_report.json'
    csv_path = out_dir / 'epstein_face_report.csv'
    html_path = out_dir / 'epstein_face_report.html'
    write_report_json(report, json_path)
    write_report_csv(report, csv_path)
    write_report_html(report, html_path)
    elapsed = time.time() - start
    print(f'Full scan complete in {elapsed/60:.1f} minutes. Reports written to {out_dir}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--gallery', required=True)
    parser.add_argument('--db', default=r'C:\Projects\FileAnalyzer\file_analyzer.db')
    parser.add_argument('--faces-out', default=r'C:\Projects\FileAnalyzer\faces_full')
    parser.add_argument('--out', default=r'C:\Projects\FileAnalyzer\reports')
    parser.add_argument('--threshold', type=float, default=0.9)
    parser.add_argument('--top-k', type=int, default=5)
    parser.add_argument('--aggregate', action='store_true')
    parser.add_argument('--limit', type=int, default=0, help='Optional limit number of files to process (0 = all)')
    args = parser.parse_args()
    run_full_scan(Path(args.root), Path(args.gallery), Path(args.db), Path(args.faces_out), Path(args.out), aggregate=args.aggregate, threshold=args.threshold, top_k=args.top_k, limit=args.limit)
