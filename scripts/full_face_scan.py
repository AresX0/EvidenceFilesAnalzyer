"""Full face pipeline: scan evidence, extract face crops from images/PDFs/videos, match against labeled gallery, persist matches and emit reports.

Usage example:
  python scripts/full_face_scan.py --evidence "C:/path/to/evidence" --gallery C:/path/to/gallery --db ./file_analyzer.db --faces-out ./faces_all --threshold 0.9 --aggregate
"""
from pathlib import Path
import argparse
import json
import logging
from case_agent.pipelines import face_search
from case_agent.pipelines.hash_inventory import walk_and_hash
from case_agent.pipelines.text_extract import extract_for_file
from case_agent.pipelines.entity_extract import extract_entities_for_file
from case_agent.pipelines.media_extract import process_media
from case_agent.reports import generate_extended_report, write_report_json, write_report_csv, write_report_html

logger = logging.getLogger('full_face_scan')
logging.basicConfig(level=logging.INFO)

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
VIDEO_EXTS = {'.mp4', '.mov', '.mkv', '.avi', '.wav', '.mp3'}
PDF_EXTS = {'.pdf'}


def crop_image_save(img_path: Path, bbox: dict, out_dir: Path, tag_prefix: str):
    """Crop an image given bbox {top,right,bottom,left} or {x,y,w,h} and save to out_dir."""
    try:
        from PIL import Image
    except Exception:
        return None
    im = Image.open(str(img_path)).convert('RGB')
    if {'top','right','bottom','left'} <= set(bbox.keys()):
        left = bbox['left']; top = bbox['top']; right = bbox['right']; bottom = bbox['bottom']
    elif {'x','y','w','h'} <= set(bbox.keys()):
        left = bbox['x']; top = bbox['y']; right = left + bbox['w']; bottom = top + bbox['h']
    else:
        return None
    crop = im.crop((left, top, right, bottom))
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{tag_prefix}_{img_path.stem}_{left}_{top}.jpg"
    crop.save(out_path)
    return out_path


def process_folder(evidence_dir: Path, gallery_dir: Path, db_path: Path, faces_out: Path, threshold: float = 0.9, top_k: int = 5, aggregate: bool = True):
    evidence_dir = Path(evidence_dir)
    gallery_dir = Path(gallery_dir)
    faces_out = Path(faces_out)

    logger.info('Initializing DB and inventorying files...')
    walk_and_hash(evidence_dir, db_path=str(db_path))

    # Process each file for text/entities/media
    logger.info('Extracting text, entities, and media where applicable...')
    for p in evidence_dir.rglob('*'):
        if p.is_file():
            try:
                extract_for_file(p, db_path=str(db_path))
                extract_entities_for_file(p, db_path=str(db_path))
                if p.suffix.lower() in VIDEO_EXTS:
                    process_media(p, faces_out, db_path=str(db_path))
            except Exception:
                logger.exception('Failed extraction for %s', p)

    # 1) PDFs: extract page crops via scripts/pdf_face_detect.py functionality
    logger.info('Detecting faces in PDFs...')
    from scripts import pdf_face_detect
    pdf_results = pdf_face_detect.run_folder(evidence_dir, faces_out / 'pdf_report.json', faces_out, limit=None)

    # 2) Images: detect and crop faces
    logger.info('Detecting faces in images...')
    from case_agent.pipelines.face_search import find_faces_in_image
    for img in evidence_dir.rglob('*'):
        if img.suffix.lower() in IMAGE_EXTS:
            try:
                dets = find_faces_in_image(img)
                for i, d in enumerate(dets):
                    bbox = d.get('bbox')
                    crop = crop_image_save(img, bbox, faces_out, 'img')
                    if crop:
                        # run labeled search and persist
                        res = face_search.search_labeled_gallery_for_image(crop, gallery_dir, threshold=threshold, top_k=top_k)
                        face_search._persist_results(db_path if db_path is not None else None, res, aggregate=aggregate)
            except Exception:
                logger.exception('Image face detection failed for %s', img)

    # 3) Videos: sample frames and persist results
    logger.info('Detecting faces in videos...')
    from case_agent.pipelines.face_search import find_faces_in_video
    for vid in evidence_dir.rglob('*'):
        if vid.suffix.lower() in VIDEO_EXTS:
            try:
                frames = find_faces_in_video(vid, interval_seconds=5.0)
                for frame in frames:
                    ts = frame.get('timestamp')
                    for i, d in enumerate(frame.get('detections', [])):
                        bbox = d.get('bbox')
                        # frame images are not available here; create a synthetic name
                        crop_path = faces_out / f"{vid.stem}_t{int(ts)}_f{i+1}.jpg"
                        # We can't easily extract the exact frame in current helper; skip saving but persist
                        res = {'source': str(vid), 'results': [{'face_bbox': bbox, 'matches': []}]}
                        # enrich by searching gallery for the face embedding if embedding available
                        face_search._persist_results(db_path if db_path is not None else None, res, aggregate=aggregate)
            except Exception:
                logger.exception('Video face detection failed for %s', vid)

    # After all crops created, run a pass to match remaining crops not yet persisted
    logger.info('Matching remaining crops in faces dir against labeled gallery...')
    for crop in faces_out.rglob('*'):
        if crop.suffix.lower() in {'.jpg', '.jpeg', '.png'}:
            try:
                res = face_search.search_labeled_gallery_for_image(crop, gallery_dir, threshold=threshold, top_k=top_k)
                face_search._persist_results(db_path if db_path is not None else None, res, aggregate=aggregate)
            except Exception:
                logger.exception('Failed to match crop %s', crop)

    logger.info('Full face scan complete')


def export_reports(db_path: Path, out_dir: Path):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = generate_extended_report(str(db_path))
    json_out = out_dir / 'epstein_face_report.json'
    csv_out = out_dir / 'epstein_face_report.csv'
    html_out = out_dir / 'epstein_face_report.html'
    write_report_json(report, json_out)
    write_report_csv(report, csv_out)
    write_report_html(report, html_out)
    logger.info('Wrote reports to %s', out_dir)
    return json_out, csv_out, html_out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', required=True)
    parser.add_argument('--gallery', required=True)
    parser.add_argument('--db', default=None, help='DB path (defaults to project DB)')
    parser.add_argument('--faces-out', default='./faces_all')
    parser.add_argument('--threshold', type=float, default=0.9)
    parser.add_argument('--top-k', type=int, default=5)
    parser.add_argument('--aggregate', action='store_true')
    parser.add_argument('--report-out', default='./reports')
    args = parser.parse_args()

    db = args.db if args.db else None
    process_folder(Path(args.evidence), Path(args.gallery), db, Path(args.faces_out), threshold=args.threshold, top_k=args.top_k, aggregate=args.aggregate)
    export_reports(db if db else None, Path(args.report_out))


if __name__ == '__main__':
    main()
