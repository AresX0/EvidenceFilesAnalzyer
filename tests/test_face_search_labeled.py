import numpy as np
from pathlib import Path
import shutil

from case_agent.pipelines import face_search


def test_labeled_gallery_matching(monkeypatch, tmp_path):
    # Create labeled gallery structure
    root = tmp_path / 'Images'
    alice = root / 'Alice'
    bob = root / 'Bob'
    alice.mkdir(parents=True)
    bob.mkdir(parents=True)

    # Create dummy images
    from PIL import Image
    img_a1 = alice / 'a1.jpg'
    img_b1 = bob / 'b1.jpg'
    Image.new('RGB', (32, 32), color='red').save(img_a1)
    Image.new('RGB', (32, 32), color='blue').save(img_b1)

    # Fake embeddings: Alice ~ vector of 0.1, Bob ~ vector of 0.9
    def fake_compute_embedding(path):
        p = str(path)
        if 'Alice' in p:
            return np.ones(128) * 0.1
        if 'Bob' in p:
            return np.ones(128) * 0.9
        # probe -> similar to Alice
        return np.ones(128) * 0.11

    monkeypatch.setattr(face_search, '_compute_embedding', fake_compute_embedding)

    # Run labeled search for a probe image
    probe = tmp_path / 'probe.jpg'
    Image.new('RGB', (32, 32), color='pink').save(probe)

    res = face_search.search_labeled_gallery_for_image(probe, root, threshold=1.5, top_k=3)
    assert res['num_subjects'] >= 1
    # Top subject should be Alice (closest to probe by fake embedding)
    top = res['subject_matches'][0]
    assert top['subject'] == 'Alice'
    assert top['matches']


def test_labeled_gallery_cache(tmp_path, monkeypatch):
    # Ensure cache builds and returns same structure
    root = tmp_path / 'Images2'
    s1 = root / 'S1'
    s1.mkdir(parents=True)
    from PIL import Image
    img = s1 / 'i.jpg'
    Image.new('RGB', (16, 16), color='white').save(img)

    monkeypatch.setattr(face_search, '_compute_embedding', lambda p: np.ones(64) * 0.2)
    labeled = face_search._load_labeled_gallery(root)
    assert 'S1' in labeled
    assert labeled['S1']
    # Second load should read cache without error
    labeled2 = face_search._load_labeled_gallery(root)
    assert 'S1' in labeled2
