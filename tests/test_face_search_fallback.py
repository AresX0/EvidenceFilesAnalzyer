import numpy as np
import types
from pathlib import Path

import pytest

from case_agent.pipelines import face_search


def test_search_image_uses_whole_image_embedding_when_no_detector(monkeypatch, tmp_path):
    # Simulate no detector available
    monkeypatch.setattr(face_search, 'face_recognition', None)
    monkeypatch.setattr(face_search, 'cv2', None)

    # Create a dummy image file
    img_path = tmp_path / 'probe.jpg'
    from PIL import Image
    Image.new('RGB', (100, 100), color='white').save(img_path)

    # Monkeypatch gallery embeddings to contain one embedding close to probe
    fake_emb = np.ones(512) * 0.5
    def fake_load_gallery_embeddings(gallery_dir):
        return {str(tmp_path / 'g1.jpg'): fake_emb}
    monkeypatch.setattr(face_search, '_load_gallery_embeddings', fake_load_gallery_embeddings)

    # Monkeypatch _compute_embedding to return a probe near the gallery embedding
    def fake_compute_embedding(path):
        return np.ones(512) * 0.5
    monkeypatch.setattr(face_search, '_compute_embedding', fake_compute_embedding)

    res = face_search.search_gallery_for_image(img_path, tmp_path, threshold=1.0, top_k=5)
    assert res['num_faces'] == 1
    assert len(res['results']) == 1
    assert res['results'][0]['matches']


def test_search_image_with_precomputed_face_embeddings(monkeypatch, tmp_path):
    # Simulate detector returns one face with embedding
    def fake_find_faces_in_image(path):
        return [{'bbox': {'top': 0, 'left': 0, 'bottom': 10, 'right': 10}, 'embedding': list(np.ones(128) * 0.2)}]
    monkeypatch.setattr(face_search, 'find_faces_in_image', fake_find_faces_in_image)

    fake_gallery_emb = {str(tmp_path / 'g1.jpg'): np.ones(128) * 0.2}
    monkeypatch.setattr(face_search, '_load_gallery_embeddings', lambda g: fake_gallery_emb)

    img_path = tmp_path / 'probe.jpg'
    from PIL import Image
    Image.new('RGB', (64, 64), color='white').save(img_path)

    res = face_search.search_gallery_for_image(img_path, tmp_path, threshold=0.5, top_k=3)
    assert res['num_faces'] == 1
    assert res['results'][0]['matches']
    assert res['results'][0]['matches'][0]['gallery_path'].endswith('g1.jpg')
