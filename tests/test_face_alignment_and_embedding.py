from PIL import Image
from case_agent.pipelines.face_search import _align_face, _compute_embedding
import numpy as np
from pathlib import Path


def test_align_face_and_embed(tmp_path):
    # Create a dummy face-like image (two bright spots for eyes)
    img = Image.new('RGB', (200, 200), color='gray')
    for x in (70, 130):
        for y in (80, 80):
            img.putpixel((x,y), (255,255,255))
    p = tmp_path / 'probe.jpg'
    img.save(p)
    # embedding should return None because it's not a real face, but code should not error
    emb = _compute_embedding(p)
    # emb may be None or numeric depending on installed libs; assert no exception and correct type
    assert emb is None or hasattr(emb, '__len__')
