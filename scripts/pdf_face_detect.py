"""Extract pages/images from PDFs, detect faces (OpenCV Haar), and save a JSON report.

Usage:
  python scripts/pdf_face_detect.py --input "C:\path\to\pdf_folder" --out ./pdf_face_results.json --faces-out ./faces
"""
from pathlib import Path
import json
import logging
from datetime import datetime

logger = logging.getLogger("pdf_face_detect")
logging.basicConfig(level=logging.INFO)

try:
    import fitz
except Exception:
    fitz = None

try:
    import cv2
    import numpy as np
except Exception:
    cv2 = None
    np = None

# Load Haar cascade once to avoid repeated disk reads and speed up detection
if cv2 is not None:
    try:
        _cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    except Exception:
        _cascade = None
else:
    _cascade = None


def detect_faces_in_image_np(img_np, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)):
    if cv2 is None:
        raise RuntimeError("OpenCV (cv2) not installed")
    gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
    cascade = _cascade if _cascade is not None else cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = cascade.detectMultiScale(gray, scaleFactor=scaleFactor, minNeighbors=minNeighbors, minSize=minSize)
    return faces.tolist() if len(faces) else []


def pix_to_numpy(pix):
    # fitz Pixmap -> numpy ndarray BGR for OpenCV
    # Preferred direct path when pix.samples is populated
    if pix.samples is None:
        # fallback: get PNG bytes and decode with OpenCV
        try:
            png_bytes = pix.tobytes("png")
            nparr = np.frombuffer(png_bytes, dtype=np.uint8)
            img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return img_np
        except Exception:
            logger.exception("Failed to convert pix to numpy via PNG fallback")
            return None

    mode = "RGB" if pix.alpha == 0 else "RGBA"
    arr = np.frombuffer(pix.samples, dtype=np.uint8)
    if mode == "RGB":
        arr = arr.reshape((pix.h, pix.w, 3))
    else:
        arr = arr.reshape((pix.h, pix.w, 4))
        arr = arr[:, :, :3]
    # fitz gives RGB; convert to BGR for OpenCV
    arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    return arr


def process_pdf(pdf_path: Path, faces_out: Path, render_zoom=2.0):
    out = {"file": str(pdf_path), "pages": []}
    if fitz is None:
        logger.error("PyMuPDF (fitz) not available; cannot extract pages")
        return out
    doc = fitz.open(str(pdf_path))
    for page_number in range(len(doc)):
        page = doc[page_number]
        mat = fitz.Matrix(render_zoom, render_zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_np = pix_to_numpy(pix)
        faces = detect_faces_in_image_np(img_np)
        page_entry = {"page": page_number + 1, "num_faces": len(faces), "faces": []}
        for i, (x, y, w, h) in enumerate(faces):
            crop = img_np[y:y+h, x:x+w]
            faces_out.mkdir(parents=True, exist_ok=True)
            crop_path = faces_out / f"{pdf_path.stem}_p{page_number+1}_f{i+1}.jpg"
            cv2.imwrite(str(crop_path), crop)
            page_entry["faces"].append({"bbox": {"x": int(x), "y": int(y), "w": int(w), "h": int(h)}, "crop": str(crop_path)})
        out["pages"].append(page_entry)
    return out


def run_folder(input_dir: Path, out_json: Path, faces_out: Path, limit=None):
    input_dir = Path(input_dir)
    pdfs = [p for p in input_dir.rglob('*.pdf')]
    results = {"generated_at": datetime.utcnow().isoformat() + 'Z', "pdfs": []}
    count = 0
    try:
        for p in sorted(pdfs):
            if limit and count >= limit:
                break
            logger.info("Processing %s", p)
            try:
                res = process_pdf(p, faces_out)
                results["pdfs"].append(res)
            except Exception as e:
                logger.exception("Failed to process %s: %s", p, e)
            count += 1
    except KeyboardInterrupt:
        logger.warning("Interrupted by user (KeyboardInterrupt); writing partial results (%d processed) to %s", count, out_json)
        out_json.parent.mkdir(parents=True, exist_ok=True)
        with out_json.open('w', encoding='utf-8') as fh:
            json.dump(results, fh, indent=2)
        return results
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with out_json.open('w', encoding='utf-8') as fh:
        json.dump(results, fh, indent=2)
    logger.info("Wrote results to %s", out_json)
    return results


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--out', default='./pdf_face_results.json')
    parser.add_argument('--faces-out', default='./faces')
    parser.add_argument('--limit', type=int, default=None, help='Optional: limit number of PDFs to process')
    args = parser.parse_args()
    run_folder(Path(args.input), Path(args.out), Path(args.faces_out), limit=args.limit)
