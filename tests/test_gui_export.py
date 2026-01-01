from pathlib import Path
from PIL import Image
from case_agent.gui.app import export_person_csv
from case_agent.pipelines.hash_inventory import sha256_file


def test_export_person_csv(tmp_path):
    # create a dummy image file
    img_path = tmp_path / 'img.jpg'
    Image.new('RGB', (320, 240), color=(123, 222, 111)).save(img_path)
    person = {'person': 'Test Subject', 'files': [str(img_path)], 'file_count': 1}
    out_dir = tmp_path / 'reports'
    csv_path = export_person_csv(person, out_dir)
    assert csv_path.exists()
    txt = csv_path.read_text(encoding='utf-8')
    assert 'Test Subject' in txt
    # verify sha and thumbnail are present
    sha = sha256_file(img_path)
    assert sha[:6] in txt
    assert 'thumbnail' in txt or '.jpg' in txt
