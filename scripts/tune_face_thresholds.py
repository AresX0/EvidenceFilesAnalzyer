"""Compute distance distributions for top matches across probes to help pick thresholds."""
from pathlib import Path
import argparse
import statistics
from case_agent.pipelines import face_search


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--faces', required=True)
    p.add_argument('--gallery', required=True)
    p.add_argument('--labeled', action='store_true')
    p.add_argument('--sample', type=int, default=0, help='Limit sample count (0=all)')
    p.add_argument('--thresholds', nargs='+', type=float, default=[0.6, 0.75, 0.9])
    args = p.parse_args()

    faces = list(Path(args.faces).glob('*'))
    if args.sample and args.sample > 0:
        faces = faces[:args.sample]

    top_distances = []
    for f in faces:
        if f.suffix.lower() not in {'.jpg', '.jpeg', '.png'}:
            continue
        if args.labeled:
            res = face_search.search_labeled_gallery_for_image(f, Path(args.gallery), threshold=9999, top_k=1)
            if res.get('subject_matches'):
                top_distances.append(res['subject_matches'][0]['best_distance'])
        else:
            res = face_search.search_gallery_for_image(f, Path(args.gallery), threshold=9999, top_k=1)
            if res.get('results'):
                # handle multiple faces; take best match across faces
                best = None
                for face in res.get('results', []):
                    for m in face.get('matches', []):
                        if best is None or m.get('distance') < best:
                            best = m.get('distance')
                if best is not None:
                    top_distances.append(best)

    if not top_distances:
        print('No matches found in sample')
        return

    print('N probes:', len(top_distances))
    print('Mean:', statistics.mean(top_distances), 'Median:', statistics.median(top_distances), 'Min:', min(top_distances), 'Max:', max(top_distances))
    for t in args.thresholds:
        cnt = sum(1 for d in top_distances if d <= t)
        print(f'Threshold <= {t}: {cnt} probes ({cnt/len(top_distances):.2%})')


if __name__ == '__main__':
    main()
