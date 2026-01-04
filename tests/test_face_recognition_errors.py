import numpy as np
from PIL import Image

from case_agent.pipelines import face_search


def test_find_faces_in_image_handles_face_recognition_exception(monkeypatch, tmp_path):
    # Create a dummy image file
    img_path = tmp_path / "probe.jpg"
    Image.new("RGB", (100, 100), color="white").save(img_path)

    # Fake face_recognition where face_locations works but face_encodings raises
    class FakeFR:
        def load_image_file(self, p):
            return np.zeros((100, 100, 3), dtype=np.uint8)

        def face_locations(self, img):
            return [(0, 10, 10, 0)]

        def face_landmarks(self, img, locs=None):
            return []

        def face_encodings(self, *args, **kwargs):
            raise RuntimeError("compute_face_descriptor error")

    monkeypatch.setattr(face_search, "face_recognition", FakeFR())

    # Should not raise and return an empty list (fallback expected)
    res = face_search.find_faces_in_image(img_path)
    assert res == []


def test_search_gallery_falls_back_to_whole_image_when_encoding_fails(
    monkeypatch, tmp_path
):
    # Create a dummy image file
    img_path = tmp_path / "probe.jpg"
    Image.new("RGB", (100, 100), color="white").save(img_path)

    # Fake FR that raises during encodings
    class FakeFR:
        def load_image_file(self, p):
            return np.zeros((100, 100, 3), dtype=np.uint8)

        def face_locations(self, img):
            return [(0, 10, 10, 0)]

        def face_landmarks(self, img, locs=None):
            return []

        def face_encodings(self, *args, **kwargs):
            raise RuntimeError("compute_face_descriptor error")

    monkeypatch.setattr(face_search, "face_recognition", FakeFR())

    # Monkeypatch gallery and embedding functions so whole-image fallback will match
    fake_emb = np.ones(128) * 0.5
    monkeypatch.setattr(
        face_search,
        "_load_gallery_embeddings",
        lambda g: {str(tmp_path / "g1.jpg"): fake_emb},
    )
    monkeypatch.setattr(face_search, "_compute_embedding", lambda p: np.ones(128) * 0.5)

    res = face_search.search_gallery_for_image(
        img_path, tmp_path, threshold=1.0, top_k=5
    )
    # Expect fallback to whole-image embedding, so one synthetic face probe should be evaluated
    assert res["num_faces"] == 1
    assert res["results"] and res["results"][0]["matches"]
