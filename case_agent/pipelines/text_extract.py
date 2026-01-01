"""Extract text from PDFs, DOCX and TXT files. Provide OCR hooks for images.

Page-level extraction is preserved where possible; each ExtractedText row should
store the page number and provenance including the originating file SHA256.
"""
from pathlib import Path
import logging
from typing import List
from ..db.init_db import get_session, init_db
from ..db.models import ExtractedText, EvidenceFile
from ..config import CHUNK_SIZE

logger = logging.getLogger("case_agent.text_extract")

# Optional dependencies
try:
    import PyPDF2
except Exception:
    PyPDF2 = None

try:
    import docx
except Exception:
    docx = None

try:
    import pytesseract
    from PIL import Image
except Exception:
    pytesseract = None


def extract_text_from_pdf(path: Path) -> List[dict]:
    pages = []
    if PyPDF2 is None:
        logger.warning("PyPDF2 not available; skipping PDF text extraction for %s", path)
        return pages
    try:
        with open(path, "rb") as fh:
            reader = PyPDF2.PdfReader(fh)
            for i, page in enumerate(reader.pages):
                try:
                    text = page.extract_text() or ""
                except Exception:
                    logger.exception('PyPDF2 failed extracting page %d of %s; will try fallback', i + 1, path)
                    text = ''
                pages.append({"page": i + 1, "text": text})
    except Exception:
        logger.exception('PyPDF2 failed to read %s; attempting PyMuPDF fallback', path)
        # Attempt PyMuPDF (fitz) fallback if available
        try:
            import fitz
            doc = fitz.open(str(path))
            for i in range(len(doc)):
                try:
                    page = doc[i]
                    text = page.get_text('text') or ''
                except Exception:
                    logger.exception('PyMuPDF failed to extract page %d for %s', i + 1, path)
                    text = ''
                pages.append({"page": i + 1, "text": text})
        except Exception:
            logger.exception('PyMuPDF fallback not available or failed for %s', path)
    # As a last resort, if pages are empty and pytesseract is available, try rasterizing pages to images and OCR
    if not any(p['text'] for p in pages):
        try:
            from PIL import Image
            import fitz
            doc = fitz.open(str(path))
            for i in range(len(doc)):
                try:
                    page = doc[i]
                    pix = page.get_pixmap(alpha=False)
                    img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
                    # OCR via pytesseract if available
                    if pytesseract is not None:
                        t = pytesseract.image_to_string(img)
                        pages.append({"page": i + 1, "text": t})
                except Exception:
                    logger.exception('Failed raster/OCR page %d for %s', i + 1, path)
        except Exception:
            logger.debug('Raster/OCR fallback not available for %s', path)
    return pages


def extract_text_from_docx(path: Path) -> List[dict]:
    pages = []
    if docx is None:
        logger.warning("python-docx not available; skipping DOCX extraction for %s", path)
        return pages
    document = docx.Document(path)
    # docx doesn't have pages; group by paragraph and return a single block
    text = "\n".join(p.text for p in document.paragraphs)
    pages.append({"page": 1, "text": text})
    return pages


def extract_text_from_txt(path: Path) -> List[dict]:
    pages = []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    pages.append({"page": 1, "text": text})
    return pages


def ocr_image(path: Path) -> List[dict]:
    pages = []
    if pytesseract is None:
        logger.warning("Tesseract not installed; OCR not available for %s", path)
        return pages
    # Ensure pytesseract uses configured tesseract binary when provided
    try:
        from ..config import TESSERACT_CMD
        pytesseract.pytesseract.tesseract_cmd = str(TESSERACT_CMD)
    except Exception:
        logger.debug("Using default tesseract on PATH for OCR")
    img = Image.open(path)
    text = pytesseract.image_to_string(img)
    pages.append({"page": 1, "text": text})
    return pages


def extract_for_file(path: Path, db_path=None):
    init_db(db_path) if db_path is not None else init_db()
    session = get_session()
    file_row = session.query(EvidenceFile).filter_by(path=str(path)).first()
    if not file_row:
        logger.error("File %s not found in DB inventory; run hash_inventory first", path)
        return []
    suffix = path.suffix.lower()
    pages = []
    try:
        if suffix == ".pdf":
            pages = extract_text_from_pdf(path)
        elif suffix in {".docx", ".doc"}:
            pages = extract_text_from_docx(path)
        elif suffix == ".txt":
            pages = extract_text_from_txt(path)
        elif suffix in {".png", ".jpg", ".jpeg", ".tiff"}:
            pages = ocr_image(path)
        else:
            logger.info("No text extraction available for %s", path)
            return []
    except Exception as e:
        logger.exception("Text extraction failed for %s: %s", path, e)
        pages = []

    # remove previous extracted pages for this file (idempotent re-run)
    try:
        session.query(ExtractedText).filter_by(file_id=file_row.id).delete()
    except Exception:
        session.rollback()

    def _sanitize_text(t: str) -> str:
        if t is None:
            return ''
        try:
            return t.encode('utf-8', 'replace').decode('utf-8')
        except Exception:
            return t

    for p in pages:
        try:
            txt = _sanitize_text(p.get("text"))
            et = ExtractedText(
                file_id=file_row.id,
                page=p.get("page"),
                text=txt,
                provenance={"sha256": file_row.sha256, "path": file_row.path},
            )
            session.add(et)
        except Exception as e:
            logger.exception("Failed to persist extracted page for %s: %s", path, e)
    try:
        session.commit()
        logger.info("Extracted %d text pages for %s", len(pages), path)
    except Exception as e:
        logger.exception("Failed to commit extracted pages for %s: %s", path, e)
    return pages


def reprocess_pdfs_without_text(db_path: str | Path = None):
    """Find PDF files that have no ExtractedText rows and re-run extraction on them.

    Returns list of processed file paths.
    """
    init_db(db_path) if db_path is not None else init_db()
    session = get_session()
    processed = []
    for f in session.query(EvidenceFile).filter(EvidenceFile.path.ilike('%.pdf')).all():
        count = session.query(ExtractedText).filter_by(file_id=f.id).count()
        if count == 0:
            p = Path(f.path)
            if p.exists():
                try:
                    extract_for_file(p, db_path=db_path)
                    processed.append(str(p))
                except Exception as e:
                    logger.exception("Failed to reprocess PDF %s: %s", p, e)
            else:
                logger.warning("PDF listed in DB not found on disk: %s", f.path)
    logger.info("Reprocessed %d PDFs with no text", len(processed))
    return processed


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extract text from files in inventory")
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args()
    for p in args.paths:
        extract_for_file(Path(p))
