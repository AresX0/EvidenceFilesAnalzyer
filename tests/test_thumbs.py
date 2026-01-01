import os
from pathlib import Path
from PIL import Image
from case_agent.utils.thumbs import thumbnail_for_image, thumbnail_for_pil_image


def test_thumbnail_for_image(tmp_path):
    p = tmp_path / "img.png"
    img = Image.new('RGB', (400, 300), color=(255, 0, 0))
    img.save(p)
    out_dir = tmp_path / "reports"
    thumb = thumbnail_for_image(str(p), out_dir, size=(160, 120))
    assert Path(thumb).exists()
    assert thumb.suffix.lower() in ['.jpg', '.jpeg']


def test_thumbnail_for_pil_image(tmp_path):
    img = Image.new('RGB', (1024, 768), color=(0, 255, 0))
    out_dir = tmp_path / "reports"
    thumb = thumbnail_for_pil_image(img, out_dir, key='testkey', size=(100, 80))
    assert Path(thumb).exists()
    assert thumb.suffix.lower() in ['.jpg', '.jpeg']
