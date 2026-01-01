from pathlib import Path
from PIL import Image
from case_agent.reports import write_report_html


def test_write_report_html_with_thumbs(tmp_path):
    # Create a fake report with one person and one image
    img = tmp_path / 'img.jpg'
    Image.new('RGB', (640, 480), color=(10, 20, 30)).save(img)
    report = {
        'counts': {'files': 1},
        'top_entities': [],
        'timeline_summary': {},
        'issues': {},
        'people': [{'person': 'Alice', 'file_count': 1, 'files': [str(img)]}],
        'pdf_synopses': []
    }
    out = tmp_path / 'reports' / 'audit.html'
    write_report_html(report, out)
    assert out.exists()
    txt = out.read_text(encoding='utf-8')
    # should link to Alice page
    assert 'people/Alice' in txt or 'Alice' in txt
    # thumbnails dir should exist
    thumbs = out.parent / 'thumbnails'
    assert thumbs.exists()
    # per-person page exists
    person_page = out.parent / 'people' / 'Alice.html'
    assert person_page.exists()
    ptxt = person_page.read_text(encoding='utf-8')
    assert 'Alice' in ptxt
    assert '.jpg' in ptxt or 'img.jpg' in ptxt
