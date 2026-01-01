from PIL import Image
from case_agent.reports import write_report_html
import json
from pathlib import Path

def test_overlay_generation(tmp_path):
    img = tmp_path / 'img.jpg'
    Image.new('RGB', (640, 480), color=(10, 20, 30)).save(img)
    report = {
        'counts': {'files': 1},
        'top_entities': [],
        'timeline_summary': {},
        'issues': {},
        'people': [{'person': 'Bob', 'file_count': 1, 'files': [str(img)]}],
        'pdf_synopses': []
    }
    out = tmp_path / 'reports' / 'audit.html'
    write_report_html(report, out)
    # check thumbnails dir exists
    thumbs = out.parent / 'thumbnails'
    assert thumbs.exists()
    person_page = out.parent / 'people' / 'Bob.html'
    assert person_page.exists()
    txt = person_page.read_text(encoding='utf-8')
    assert 'img.jpg' in txt
