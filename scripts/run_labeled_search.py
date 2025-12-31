from pathlib import Path
import json
from case_agent.pipelines import face_search

faces_dir = Path(r"C:\Projects\FileAnalyzer\faces_0001")
gallery = Path(r"C:\Projects\FileAnalyzer\Images")
out = Path(r"C:\Projects\FileAnalyzer\face_match_labeled_all.json")
res_list = []
for p in sorted(faces_dir.glob('*.jpg')):
    try:
        r = face_search.search_labeled_gallery_for_image(p, gallery, threshold=1.0, top_k=5)
        res_list.append(r)
    except Exception as e:
        print('Error for', p, e)
with out.open('w', encoding='utf-8') as fh:
    json.dump(res_list, fh, indent=2)
print('Wrote', out)
