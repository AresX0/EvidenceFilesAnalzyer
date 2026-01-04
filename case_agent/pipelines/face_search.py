"""Face detection and comparison pipeline.

Uses local libraries (face_recognition or DeepFace/OpenCV) when available. All
operations are local and auditable; gallery embeddings are cached for speed.
"""

import json
import logging
import math
import pickle
from pathlib import Path

logger = logging.getLogger("case_agent.face_search")

# Try common face libs
try:
    import face_recognition
except Exception:
    face_recognition = None

try:
    import cv2
except Exception:
    cv2 = None

# facenet-pytorch fallback for embeddings when dlib/face_recognition isn't available
try:
    import torch
    from facenet_pytorch import InceptionResnetV1

    _facenet_model = None
except Exception:
    InceptionResnetV1 = None
    torch = None
    _facenet_model = None


def _ensure_facenet_model():
    global _facenet_model
    if _facenet_model is None and InceptionResnetV1 is not None:
        _facenet_model = InceptionResnetV1(pretrained="vggface2").eval()
    return _facenet_model


def _load_gallery_embeddings(gallery_dir: Path) -> dict:
    cache = gallery_dir / ".face_cache.pkl"
    if cache.exists():
        try:
            with cache.open("rb") as fh:
                return pickle.load(fh)
        except Exception:
            logger.exception("Failed to load gallery cache; will rebuild")
    embeddings = {}
    for p in gallery_dir.rglob("*"):
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"}:
            emb = _compute_embedding(p)
            if emb is not None:
                embeddings[str(p)] = emb
    try:
        with cache.open("wb") as fh:
            pickle.dump(embeddings, fh)
    except Exception:
        logger.exception("Failed to write gallery cache")
    return embeddings


def _load_labeled_gallery(labeled_dir: Path) -> dict:
    """Load a labeled gallery (subfolders = subjects) and cache embeddings.

    Returns a dict {subject: [{'path': str(path), 'embedding': list}]}.
    """
    labeled_dir = Path(labeled_dir)
    cache = labeled_dir / ".labeled_face_cache.pkl"
    if cache.exists():
        try:
            with cache.open("rb") as fh:
                return pickle.load(fh)
        except Exception:
            logger.exception("Failed to load labeled gallery cache; will rebuild")
    out = {}
    for sub in sorted(labeled_dir.iterdir()):
        if not sub.is_dir():
            continue
        items = []
        for p in sub.rglob("*"):
            if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"}:
                emb = _compute_embedding(p)
                if emb is not None:
                    items.append(
                        {
                            "path": str(p),
                            "embedding": (
                                emb.tolist() if hasattr(emb, "tolist") else list(emb)
                            ),
                        }
                    )
        if items:
            out[sub.name] = items
    try:
        labeled_dir.mkdir(parents=True, exist_ok=True)
        with cache.open("wb") as fh:
            pickle.dump(out, fh)
    except Exception:
        logger.exception("Failed to write labeled gallery cache")
    return out


def _align_face(pil_img, landmarks):
    """Align face to canonical orientation using eye positions from landmarks.

    Expects PIL Image and landmarks dict from face_recognition.face_landmarks.
    Returns a resized (160x160) PIL Image suitable for embedding.
    """
    try:
        import math

        from PIL import Image
    except Exception:
        return None
    # Get eye center points
    left_eye = landmarks.get("left_eye")
    right_eye = landmarks.get("right_eye")
    if not left_eye or not right_eye:
        return None

    def centroid(points):
        x = sum(p[0] for p in points) / len(points)
        y = sum(p[1] for p in points) / len(points)
        return (x, y)

    le = centroid(left_eye)
    re = centroid(right_eye)
    # Compute angle between eyes
    dx = re[0] - le[0]
    dy = re[1] - le[1]
    angle = math.degrees(math.atan2(dy, dx))
    # Rotate image around center to make eyes horizontal
    cx, cy = pil_img.size[0] / 2, pil_img.size[1] / 2
    rotated = pil_img.rotate(
        -angle, resample=Image.BICUBIC, center=(cx, cy), expand=False
    )
    # Crop around center square and resize to 160x160
    w, h = rotated.size
    side = min(w, h)
    left = int((w - side) // 2)
    top = int((h - side) // 2)
    crop = rotated.crop((left, top, left + side, top + side)).resize(
        (160, 160), Image.LANCZOS
    )
    return crop


def _compute_embedding(image_input):
    """Compute an embedding for an image file or image object.

    Accepts a Path to an image file, a PIL Image, or a numpy array (RGB or BGR).
    Tries (in order): face_recognition (dlib with optional alignment), facenet-pytorch, then returns None.
    """
    # Normalize input to numpy RGB array or PIL Image depending on library
    pil_img = None
    np_img = None
    try:
        from PIL import Image
    except Exception:
        Image = None
    # If a Path-like was provided, load it
    if isinstance(image_input, (str, Path)):
        p = str(image_input)
        if face_recognition is not None:
            try:
                img = face_recognition.load_image_file(p)
                np_img = img
            except Exception:
                logger.exception("face_recognition failed to load image %s", p)
        if np_img is None and Image is not None:
            try:
                pil_img = Image.open(p).convert("RGB")
            except Exception:
                logger.exception("PIL failed to load image %s", p)
    else:
        # Assume it's a numpy array or PIL Image
        if Image is not None and isinstance(image_input, Image.Image):
            pil_img = image_input
        else:
            try:
                import numpy as _np

                if isinstance(image_input, _np.ndarray):
                    np_img = image_input
                else:
                    # Unknown input
                    pass
            except Exception:
                pass

    # 1) Try face_recognition (dlib) with alignment
    if face_recognition is not None:
        try:
            # If we have np_img, pass it directly; otherwise convert pil_img to np
            if np_img is None and pil_img is not None:
                np_img = _pil_to_np(pil_img)
            face_locs = (
                face_recognition.face_locations(np_img) if np_img is not None else []
            )
            if face_locs:
                # pick largest face bbox
                loc = max(
                    face_locs,
                    key=lambda loc: (loc[2] - loc[0])
                    * (loc[1] - loc[3] if loc[1] > loc[3] else loc[3] - loc[1]),
                )
                # landmarks
                landmarks_list = face_recognition.face_landmarks(np_img, [loc])
                if landmarks_list:
                    landmarks = landmarks_list[0]
                    # convert np image to PIL for alignment
                    if pil_img is None and np_img is not None:
                        pil_img = _np_to_pil(np_img)
                    aligned = _align_face(pil_img, landmarks)
                    if aligned is not None:
                        encs = face_recognition.face_encodings(_pil_to_np(aligned))
                        if encs:
                            return encs[0]
                # fallback: face_recognition enc on original
                encs = face_recognition.face_encodings(np_img)
                if encs:
                    return encs[0]
        except Exception:
            logger.exception("face_recognition embedding failed for input")

    # 2) Try facenet-pytorch on aligned or resized PIL image
    if InceptionResnetV1 is not None:
        try:
            if pil_img is None and np_img is not None:
                pil_img = _np_to_pil(np_img)
            if pil_img is None:
                return None
            # Try to detect landmarks with face_recognition if available so we can align
            aligned_img = None
            if face_recognition is not None:
                try:
                    np_tmp = _pil_to_np(pil_img)
                    locs = face_recognition.face_locations(np_tmp)
                    if locs:
                        best_loc = max(
                            locs,
                            key=lambda cand: (cand[2] - cand[0])
                            * (
                                cand[1] - cand[3]
                                if cand[1] > cand[3]
                                else cand[3] - cand[1]
                            ),
                        )
                        lds = face_recognition.face_landmarks(np_tmp, [best_loc])
                        if lds:
                            aligned_img = _align_face(pil_img, lds[0])
                except Exception:
                    pass
            img = aligned_img if aligned_img is not None else pil_img
            model = _ensure_facenet_model()
            if model is None:
                return None
            # Resize/crop to 160x160 as standard for FaceNet inputs
            img = img.resize((160, 160))
            import torchvision.transforms as transforms

            transform = transforms.Compose(
                [
                    transforms.ToTensor(),
                    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
                ]
            )
            t = transform(img).unsqueeze(0)
            with torch.no_grad():
                v = model(t)
            return v.squeeze(0).cpu().numpy()
        except Exception:
            logger.exception("facenet-pytorch embedding failed for input")
    logger.warning("No embedding method available for input")
    return None


def _pil_to_np(img):
    """Convert PIL Image (RGB) to numpy array (RGB)"""
    import numpy as _np

    return _np.array(img)


def _np_to_pil(arr):
    """Convert numpy array (RGB or BGR) to PIL Image (RGB)"""
    try:
        from PIL import Image
    except Exception:
        return None

    if arr.ndim == 3 and arr.shape[2] == 3:
        # Try to detect if it's BGR (common with OpenCV); assume values 0-255
        # Heuristic: if mean of first channel is greater than mean of last channel, treat as BGR
        if arr[:, :, 0].mean() > arr[:, :, 2].mean():
            arr = arr[:, :, ::-1]
        return Image.fromarray(arr.astype("uint8"))
    if arr.ndim == 2:
        return Image.fromarray(arr.astype("uint8"))
    return None


def _compare_embedding(enc1, enc2):
    # Euclidean distance
    if enc1 is None or enc2 is None:
        return math.inf
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(enc1, enc2)))


def find_faces_in_image(image_path: Path):
    """Return list of detected faces with bounding boxes and embeddings.

    Uses face_recognition if available; otherwise tries OpenCV Haar cascade if cv2
    is present. Each returned entry is {'bbox': {...}, 'embedding': [...]}.
    """
    # 1) Try face_recognition (dlib)
    if face_recognition is not None:
        try:
            img = face_recognition.load_image_file(str(image_path))
            locations = face_recognition.face_locations(img)
            encs = face_recognition.face_encodings(img, locations)
            out = []
            for loc, enc in zip(locations, encs):
                # loc is (top, right, bottom, left)
                out.append(
                    {
                        "bbox": {
                            "top": int(loc[0]),
                            "right": int(loc[1]),
                            "bottom": int(loc[2]),
                            "left": int(loc[3]),
                        },
                        "embedding": enc.tolist(),
                    }
                )
            return out
        except Exception:
            logger.exception(
                "face_recognition detection/encoding failed for %s", image_path
            )
            # Fall through to fallback methods (OpenCV or whole-image embedding).

    # 2) Fallback to OpenCV Haar cascade if available
    if cv2 is not None:
        try:
            # Read image with cv2 and detect faces
            img = cv2.imread(str(image_path))
            if img is None:
                logger.error("cv2 failed to read image %s", image_path)
                return []
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            casc_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            cascade = cv2.CascadeClassifier(casc_path)
            rects = cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
            )
            out = []
            for x, y, w, h in rects:
                top, left, bottom, right = int(y), int(x), int(y + h), int(x + w)
                crop = img[top:bottom, left:right]
                emb = _compute_embedding(crop)
                if emb is not None:
                    out.append(
                        {
                            "bbox": {
                                "top": top,
                                "right": right,
                                "bottom": bottom,
                                "left": left,
                            },
                            "embedding": (
                                emb.tolist() if hasattr(emb, "tolist") else list(emb)
                            ),
                        }
                    )
            return out
        except Exception:
            logger.exception("OpenCV Haar face detection failed for %s", image_path)
            return []

    logger.warning("No face detection method available for %s", image_path)
    return []


def find_faces_in_video(video_path: Path, interval_seconds: float = 5.0):
    """Sample frames and run face detection on them. Returns list of detections per timestamp."""
    if cv2 is None:
        logger.warning(
            "opencv (cv2) not installed; cannot sample video frames for %s", video_path
        )
        return []
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        logger.error("Failed to open video %s", video_path)
        return []
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    duration = total / fps if fps else 0
    ts = 0.0
    results = []
    while ts < duration:
        frame_no = int(ts * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
        ret, frame = cap.read()
        if not ret:
            break
        # Convert BGR -> RGB for face_recognition
        rgb = frame[:, :, ::-1]
        if face_recognition is None:
            break
        try:
            locations = face_recognition.face_locations(rgb)
            encs = face_recognition.face_encodings(rgb, locations)
        except Exception:
            logger.exception(
                "face_recognition detection/encoding failed for frame at %s in %s",
                ts,
                video_path,
            )
            ts += interval_seconds
            continue
        dets = []
        for loc, enc in zip(locations, encs):
            dets.append(
                {
                    "bbox": {
                        "top": int(loc[0]),
                        "right": int(loc[1]),
                        "bottom": int(loc[2]),
                        "left": int(loc[3]),
                    },
                    "embedding": enc.tolist(),
                }
            )
        if dets:
            results.append({"timestamp": ts, "detections": dets})
        ts += interval_seconds
    cap.release()
    return results


def search_gallery_for_image(
    image_path: Path, gallery_dir: Path, threshold: float = 0.6, top_k: int = 5
):
    """Detect faces in image and compare to gallery. Returns matches per face.

    If no face detector is available or detection finds nothing, fall back to
    computing an embedding for the whole image and comparing that single probe.
    """
    gallery_dir = Path(gallery_dir)
    gallery_embs = _load_gallery_embeddings(gallery_dir)
    faces = find_faces_in_image(image_path)
    out = []

    # If detector not available or no faces found, treat the whole image as a single probe
    if not faces:
        logger.info(
            "No faces detected (or detector unavailable) for %s; using whole-image embedding as a probe",
            image_path,
        )
        probe_emb = _compute_embedding(image_path)
        if probe_emb is None:
            return {"source": str(image_path), "num_faces": 0, "results": []}
        best = []
        for gp, genc in gallery_embs.items():
            dist = _compare_embedding(probe_emb, genc)
            if dist <= threshold:
                best.append({"gallery_path": gp, "distance": dist})
        best.sort(key=lambda x: x["distance"])
        return {
            "source": str(image_path),
            "num_faces": 1,
            "results": [{"face_bbox": None, "matches": best[:top_k]}],
        }

    for face in faces:
        enc = face.get("embedding")
        best = []
        for gp, genc in gallery_embs.items():
            dist = _compare_embedding(enc, genc)
            if dist <= threshold:
                best.append({"gallery_path": gp, "distance": dist})
        best.sort(key=lambda x: x["distance"])
        out.append({"face_bbox": face.get("bbox"), "matches": best[:top_k]})
    return {"source": str(image_path), "num_faces": len(faces), "results": out}


def search_gallery_for_video(
    video_path: Path,
    gallery_dir: Path,
    interval_seconds: float = 5.0,
    threshold: float = 0.6,
    top_k: int = 3,
):
    gallery_dir = Path(gallery_dir)
    gallery_embs = _load_gallery_embeddings(gallery_dir)
    frames = find_faces_in_video(video_path, interval_seconds=interval_seconds)
    out = []
    for frame in frames:
        ts = frame.get("timestamp")
        dets = []
        for d in frame.get("detections", []):
            enc = d.get("embedding")
            best = []
            for gp, genc in gallery_embs.items():
                dist = _compare_embedding(enc, genc)
                if dist <= threshold:
                    best.append({"gallery_path": gp, "distance": dist})
            best.sort(key=lambda x: x["distance"])
            dets.append({"bbox": d.get("bbox"), "matches": best[:top_k]})
        if dets:
            out.append({"timestamp": ts, "detections": dets})
    return {"source": str(video_path), "frames_with_matches": len(out), "results": out}


# Labeled gallery helpers (subfolders = subject names)
def _compute_subject_embeddings(labeled: dict) -> dict:
    """Given labeled gallery dict {subject: [{path, embedding}]}, compute a representative
    subject embedding (L2-normalized mean) for each subject."""
    import numpy as _np

    out = {}
    for subject, items in labeled.items():
        embs = [
            (_np.array(it["embedding"], dtype="float32"))
            for it in items
            if it.get("embedding") is not None
        ]
        if not embs:
            continue
        # L2-normalize each embedding then average and renormalize
        embs = [_np.asarray(e) for e in embs]
        norms = [_np.linalg.norm(e) for e in embs]
        embs_normed = [e / (n if n else 1.0) for e, n in zip(embs, norms)]
        mean = _np.mean(embs_normed, axis=0)
        norm = _np.linalg.norm(mean)
        if norm:
            mean = mean / norm
        out[subject] = mean
    return out


def search_labeled_gallery_for_image(
    image_path: Path,
    labeled_gallery_dir: Path,
    threshold: float = 0.6,
    top_k: int = 5,
    use_subject_embeddings: bool = True,
):
    labeled = _load_labeled_gallery(labeled_gallery_dir)
    probe = _compute_embedding(image_path)
    if probe is None:
        return {"source": str(image_path), "num_subjects": 0, "subject_matches": []}

    # Optionally compute subject-level embeddings and compare first (faster, more robust)
    subject_matches = []
    if use_subject_embeddings:
        subj_embs = _compute_subject_embeddings(labeled)
        for subject, s_emb in subj_embs.items():
            dist = _compare_embedding(probe, s_emb)
            if dist <= threshold:
                subject_matches.append(
                    {"subject": subject, "best_distance": float(dist), "matches": []}
                )
        # sort for top-k and if threshold filters none, fall back to image-level
        subject_matches.sort(key=lambda x: x["best_distance"])
        if subject_matches:
            # For each candidate subject, gather image-level matches as details
            for m in subject_matches[:top_k]:
                items = labeled.get(m["subject"], [])
                best = []
                for item in items:
                    d = _compare_embedding(probe, item.get("embedding"))
                    best.append({"path": item.get("path"), "distance": float(d)})
                best.sort(key=lambda x: x["distance"])
                m["matches"] = best[:top_k]
            return {
                "source": str(image_path),
                "num_subjects": len(subject_matches),
                "subject_matches": subject_matches,
            }

    # Fallback: exhaustive image-level comparison
    for subject, items in labeled.items():
        best = []
        for item in items:
            dist = _compare_embedding(probe, item.get("embedding"))
            if dist <= threshold:
                best.append({"path": item.get("path"), "distance": float(dist)})
        if best:
            best.sort(key=lambda x: x["distance"])
            subject_matches.append(
                {
                    "subject": subject,
                    "best_distance": best[0]["distance"],
                    "matches": best[:top_k],
                }
            )
    subject_matches.sort(key=lambda x: x["best_distance"])
    return {
        "source": str(image_path),
        "num_subjects": len(subject_matches),
        "subject_matches": subject_matches,
    }


def aggregate_subject_summary(res: dict):
    """Return per-subject summary list of {'subject','best_distance','best_path'} for labeled results."""
    out = []
    if "subject_matches" not in res:
        return out
    for sm in res.get("subject_matches", []):
        subject = sm.get("subject")
        best = None
        for m in sm.get("matches", []):
            if best is None or m.get("distance") < best.get("distance"):
                best = m
        if best is not None:
            out.append(
                {
                    "subject": subject,
                    "best_distance": best.get("distance"),
                    "best_path": best.get("path"),
                }
            )
    return out


def _persist_results(db_path: str | Path, res: dict, aggregate: bool = False):
    """Persist face search results into SQLAlchemy-managed DB using FaceMatch model.

    If aggregate=True and results are labeled, persist only the best match per subject.
    """
    import datetime

    from ..db.init_db import get_session, init_db
    from ..db.models import FaceMatch

    # Initialize DB and get session
    init_db(db_path)
    session = get_session()
    now = datetime.datetime.now(datetime.timezone.utc)
    source = res.get("source")

    # Labeled gallery format
    if "subject_matches" in res:
        if aggregate:
            summary = aggregate_subject_summary(res)
            for s in summary:
                fm = FaceMatch(
                    source=source,
                    probe_bbox=None,
                    subject=s.get("subject"),
                    gallery_path=s.get("best_path"),
                    distance=float(s.get("best_distance")),
                    created_at=now,
                )
                session.add(fm)
        else:
            for sm in res.get("subject_matches", []):
                subject = sm.get("subject")
                for m in sm.get("matches", []):
                    fm = FaceMatch(
                        source=source,
                        probe_bbox=None,
                        subject=subject,
                        gallery_path=m.get("path"),
                        distance=float(m.get("distance")),
                        created_at=now,
                    )
                    session.add(fm)
    else:
        # Unlabeled: multiple faces; aggregate=True will persist only top match per face
        for face in res.get("results", []):
            bbox = face.get("face_bbox")
            if aggregate:
                best = None
                for m in face.get("matches", []):
                    if best is None or m.get("distance") < best.get("distance"):
                        best = m
                if best:
                    fm = FaceMatch(
                        source=source,
                        probe_bbox=bbox,
                        subject=None,
                        gallery_path=best.get("gallery_path"),
                        distance=float(best.get("distance")),
                        created_at=now,
                    )
                    session.add(fm)
                    # If there is no gallery_path (no match), copy the source crop into Images/unidentified for later processing
                    try:
                        if (
                            not best.get("gallery_path")
                            and source
                            and Path(source).exists()
                        ):
                            outdir = Path("Images") / "unidentified"
                            outdir.mkdir(parents=True, exist_ok=True)
                            dst = outdir / Path(source).name
                            if not dst.exists():
                                import shutil

                                shutil.copy2(source, dst)
                    except Exception:
                        pass
            else:
                for m in face.get("matches", []):
                    fm = FaceMatch(
                        source=source,
                        probe_bbox=bbox,
                        subject=None,
                        gallery_path=m.get("gallery_path"),
                        distance=float(m.get("distance")),
                        created_at=now,
                    )
                    session.add(fm)
                    try:
                        if (
                            not m.get("gallery_path")
                            and source
                            and Path(source).exists()
                        ):
                            outdir = Path("Images") / "unidentified"
                            outdir.mkdir(parents=True, exist_ok=True)
                            dst = outdir / Path(source).name
                            if not dst.exists():
                                import shutil

                                shutil.copy2(source, dst)
                    except Exception:
                        pass
    session.commit()


def cli_run(args):
    p = Path(args.path)
    gallery = Path(args.gallery)
    if not gallery.exists():
        raise SystemExit("Gallery dir does not exist: " + str(gallery))
    if getattr(args, "labeled", False):
        if p.suffix.lower() in {".jpg", ".jpeg", ".png"}:
            res = search_labeled_gallery_for_image(
                p, gallery, threshold=args.threshold, top_k=args.top_k
            )
        else:
            raise SystemExit("Labeled search only supports images")
    else:
        if p.suffix.lower() in {".jpg", ".jpeg", ".png"}:
            res = search_gallery_for_image(
                p, gallery, threshold=args.threshold, top_k=args.top_k
            )
        else:
            res = search_gallery_for_video(
                p,
                gallery,
                interval_seconds=args.interval,
                threshold=args.threshold,
                top_k=args.top_k,
            )

    # Optionally persist to DB
    if getattr(args, "persist_db", None):
        try:
            _persist_results(args.persist_db, res)
            print("Persisted face matches to DB:", args.persist_db)
        except Exception:
            logger.exception("Failed to persist face matches to DB %s", args.persist_db)

    out = Path(args.out) if args.out else None
    if out:
        with out.open("w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=2)
        print("Wrote face search results to", out)
    else:
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True)
    parser.add_argument("--gallery", required=True)
    parser.add_argument("--out")
    parser.add_argument("--threshold", type=float, default=0.6)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--interval", type=float, default=5.0)
    args = parser.parse_args()
    cli_run(args)
