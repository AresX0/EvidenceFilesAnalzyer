"""Sweep face crops and persist matches to DB.

Usage examples:
  python scripts/persist_all_face_matches.py --faces C:\Projects\FileAnalyzer\faces_0001 --gallery C:\Projects\FileAnalyzer\Images --labeled --db C:\Projects\FileAnalyzer\file_analyzer.db --threshold 0.9
"""
from pathlib import Path
import argparse
import json
from case_agent.pipelines import face_search


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--faces', required=True, help='Directory with face crops')
    p.add_argument('--gallery', required=True, help='Gallery directory (images or labeled subfolders)')
    p.add_argument('--labeled', action='store_true', help='Treat gallery as labeled (subfolders = subject)')
    p.add_argument('--db', default=None, help='SQLite DB path to persist into (defaults to project DB)')
    p.add_argument('--threshold', type=float, default=1.0)
    p.add_argument('--top-k', type=int, default=5)
    p.add_argument('--aggregate', action='store_true', help='Persist only best match per subject/face')
    args = p.parse_args()

    faces_dir = Path(args.faces)
    gallery = Path(args.gallery)
    db = args.db
    if not faces_dir.exists():
        raise SystemExit('Faces dir does not exist: ' + str(faces_dir))
    if not gallery.exists():
        raise SystemExit('Gallery dir does not exist: ' + str(gallery))

    total = 0
    persisted = 0
    for pth in sorted(faces_dir.glob('*')):
        if pth.suffix.lower() not in {'.jpg', '.jpeg', '.png'}:
            continue
        total += 1
        try:
            if args.labeled:
                res = face_search.search_labeled_gallery_for_image(pth, gallery, threshold=args.threshold, top_k=args.top_k)
            else:
                res = face_search.search_gallery_for_image(pth, gallery, threshold=args.threshold, top_k=args.top_k)
            if db:
                face_search._persist_results(db, res, aggregate=args.aggregate)
            else:
                # persist to default DB
                face_search._persist_results(None, res, aggregate=args.aggregate)
            persisted += 1
        except Exception as e:
            print('Error processing', pth, e)
    print(f'Processed {total} face crops; persisted {persisted} results')


if __name__ == '__main__':
    main()
