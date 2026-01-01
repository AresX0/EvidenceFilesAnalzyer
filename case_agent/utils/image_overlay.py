"""Utilities to draw face match overlays on images for GUI preview and thumbnails.

Functions:
- overlay_matches_on_pil(img, matches, size=None) -> PIL.Image with rectangles and labels
  where matches is list of {'probe_bbox': {'top','left','bottom','right'}, 'subject': str}

- render_pdf_first_page(path, size) -> PIL.Image rendering first page using fitz (PyMuPDF) if available
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None


def overlay_matches_on_pil(img: Image.Image, matches: list, size: tuple | None = None) -> Image.Image:
    """Draw rectangles and subject labels on a PIL image. Matches bbox uses pixel coords.

    If size is provided, image will be resized (thumbnail) before drawing and bboxes scaled.
    """
    orig_w, orig_h = img.size
    if size is not None:
        img = img.copy()
        img.thumbnail(size)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    w, h = img.size
    for m in matches:
        bbox = m.get('probe_bbox') or m.get('face_bbox')
        if not bbox:
            continue
        # bbox may be dict with top/left/bottom/right or list [x1,y1,x2,y2]
        if isinstance(bbox, dict):
            top = bbox.get('top')
            left = bbox.get('left')
            bottom = bbox.get('bottom')
            right = bbox.get('right')
        elif isinstance(bbox, (list, tuple)) and len(bbox) == 4:
            left, top, right, bottom = bbox
        else:
            continue
        # scale coordinates from original to current img size
        sx = w / orig_w
        sy = h / orig_h
        l = int(left * sx)
        t = int(top * sy)
        r = int(right * sx)
        b = int(bottom * sy)
        # draw rectangle
        draw.rectangle([l, t, r, b], outline='lime', width=max(1, int(min(w, h) / 200)))
        name = m.get('subject') or ''
        if name:
            text = str(name)
            # text size - use font.getsize when available, fallback to textbbox
            try:
                if font is not None:
                    text_w, text_h = font.getsize(text)
                else:
                    text_w, text_h = draw.textsize(text)
            except Exception:
                try:
                    bbox = draw.textbbox((0,0), text, font=font)
                    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
                except Exception:
                    text_w, text_h = (50, 10)
            # filled rectangle behind text
            draw.rectangle([l, t - text_h - 4, l + text_w + 6, t], fill='lime')
            draw.text((l + 3, t - text_h - 2), text, fill='black', font=font)
    return img


def render_pdf_first_page(path: str | Path, size=(160, 120)) -> Image.Image:
    p = Path(path)
    if fitz is None:
        # fallback to placeholder
        img = Image.new('RGB', size, color=(200, 200, 200))
        return img
    doc = fitz.open(str(p))
    if doc.page_count < 1:
        return Image.new('RGB', size, color=(200, 200, 200))
    page = doc.load_page(0)
    mat = fitz.Matrix(2, 2)
    pix = page.get_pixmap(matrix=mat)
    mode = 'RGB' if pix.n < 4 else 'RGBA'
    img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
    img.thumbnail(size)
    return img
