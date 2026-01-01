"""Thumbnail utilities for derived image assets (saved under reports/thumbnails).

Functions:
- ensure_thumbnails_dir(out_dir) -> Path
- thumbnail_for_image(path, out_dir, size=(160,160)) -> Path (thumbnail file path)
- thumbnail_for_pil_image(pil_img, out_dir, key=None, size=(160,160)) -> Path

Thumbnails are cached by file sha256 (or key) to avoid regenerating.
"""
from pathlib import Path
from io import BytesIO
import hashlib
from PIL import Image

from case_agent.pipelines.hash_inventory import sha256_file

THUMB_SUBDIR = "thumbnails"


def ensure_thumbnails_dir(out_dir: Path) -> Path:
    out_dir = Path(out_dir)
    td = out_dir / THUMB_SUBDIR
    td.mkdir(parents=True, exist_ok=True)
    return td


def _thumb_filename_from_hash(h: str, size=(160, 160)) -> str:
    return f"{h}_{size[0]}x{size[1]}.jpg"


def thumbnail_for_image(image_path: str, out_dir: str | Path, size=(160, 160)) -> Path:
    """Create (or reuse) a thumbnail JPG for the given image file.

    Returns the Path to the generated thumbnail.
    """
    image_path = Path(image_path)
    out_dir = Path(out_dir)
    td = ensure_thumbnails_dir(out_dir)
    try:
        sha = sha256_file(image_path)
    except Exception:
        # fallback to file name hash
        h = hashlib.sha256(str(image_path).encode('utf-8')).hexdigest()
        sha = h
    fname = _thumb_filename_from_hash(sha, size)
    out_path = td / fname
    if out_path.exists():
        return out_path
    try:
        # Support PDF thumbnails via PyMuPDF if available
        if image_path.suffix.lower() == '.pdf':
            try:
                from .image_overlay import render_pdf_first_page
                pil = render_pdf_first_page(image_path, size=size)
                pil.save(out_path, format='JPEG', quality=85)
                return out_path
            except Exception:
                pass
        img = Image.open(image_path)
        img = img.convert('RGB')
        img.thumbnail(size)
        img.save(out_path, format='JPEG', quality=85)
        return out_path
    except Exception:
        # If the image can't be opened, make a placeholder
        placeholder = Image.new('RGB', size, color=(200, 200, 200))
        placeholder.save(out_path, format='JPEG', quality=85)
        return out_path


def thumbnail_for_pil_image(pil_img: Image.Image, out_dir: str | Path, key: str | None = None, size=(160, 160)) -> Path:
    """Create a thumbnail from a PIL image instance; key (if provided) will be hashed to name the file."""
    out_dir = Path(out_dir)
    td = ensure_thumbnails_dir(out_dir)
    if key is None:
        # derive a quick hash from image bytes
        buf = BytesIO()
        pil_img.save(buf, format='PNG')
        digest = hashlib.sha256(buf.getvalue()).hexdigest()
    else:
        digest = hashlib.sha256(key.encode('utf-8')).hexdigest()
    fname = _thumb_filename_from_hash(digest, size)
    out_path = td / fname
    if out_path.exists():
        return out_path
    try:
        img = pil_img.convert('RGB')
        img.thumbnail(size)
        img.save(out_path, format='JPEG', quality=85)
        return out_path
    except Exception:
        placeholder = Image.new('RGB', size, color=(200, 200, 200))
        placeholder.save(out_path, format='JPEG', quality=85)
        return out_path
