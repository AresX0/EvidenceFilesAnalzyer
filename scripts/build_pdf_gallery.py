"""Render PDF pages to images for building a gallery of images to match against.

Usage:
  python scripts/build_pdf_gallery.py --input "C:\path\to\pdf_folder" --out_gallery C:\Projects\FileAnalyzer\gallery_0002 --limit 100
"""
from pathlib import Path
import logging
from datetime import datetime

logger = logging.getLogger("build_pdf_gallery")
logging.basicConfig(level=logging.INFO)

try:
    import fitz
except Exception:
    fitz = None


def render_pdf_to_images(pdf_path: Path, out_dir: Path, zoom=1.0):
    out = []
    if fitz is None:
        logger.error("PyMuPDF (fitz) not available; cannot render %s", pdf_path)
        return out
    doc = fitz.open(str(pdf_path))
    for i in range(len(doc)):
        page = doc[i]
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        out_dir.mkdir(parents=True, exist_ok=True)
        img_path = out_dir / f"{pdf_path.stem}_p{i+1}.png"
        pix.save(str(img_path))
        out.append(str(img_path))
    return out


def build_gallery(input_dir: Path, out_gallery: Path, limit=None):
    input_dir = Path(input_dir)
    pdfs = sorted(list(input_dir.rglob('*.pdf')))
    out = {"generated_at": datetime.utcnow().isoformat() + 'Z', "images": []}
    count = 0
    for p in pdfs:
        if limit and count >= limit:
            break
        logger.info("Rendering %s", p)
        try:
            files = render_pdf_to_images(p, out_gallery / p.stem)
            out["images"].extend(files)
        except Exception as e:
            logger.exception('Failed to render %s: %s', p, e)
        count += 1
    return out


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--out-gallery', required=True)
    parser.add_argument('--limit', type=int, default=None)
    args = parser.parse_args()
    res = build_gallery(Path(args.input), Path(args.out_gallery), limit=args.limit)
    print('Rendered', len(res['images']), 'images')
