from pathlib import Path
from PIL import Image
from case_agent.reports import write_report_html


def test_overlay_generated_using_face_matches_map(tmp_path):
    # create an image
    img_path = tmp_path / 'img.jpg'
    Image.new('RGB', (400, 300), color=(255, 255, 255)).save(img_path)
    people = [{'person': 'Alice', 'files': [str(img_path)], 'file_count': 1}]
    # make a fake thumbnail name by invoking write_report_html which will create thumbnails
    report = {'counts': {}, 'people': people, 'face_matches_map': {str(img_path): [{'subject': 'Alice', 'probe_bbox': {'top': 10, 'left': 10, 'bottom': 50, 'right': 50}}]}}
    out = tmp_path / 'report.html'
    write_report_html(report, out)
    # person page and overlay should exist
    people_dir = tmp_path / 'people'
    safe_name = 'Alice'
    ppage = people_dir / f"{safe_name}.html"
    assert ppage.exists()
    txt = ppage.read_text(encoding='utf-8')
    assert 'overlay_' in txt or 'img.jpg' in txt
    # check overlay image exists in report dir
    # look for file starting with overlay_
    overlays = list(tmp_path.glob('overlay_*'))
    assert overlays, 'No overlay image generated'