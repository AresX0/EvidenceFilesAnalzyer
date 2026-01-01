"""Alfred: simple query interface to list evidence files by person.

Functions:
- parse_query(text) -> dict (action, type, person)
- list_files_for_person(db_path, person, type='images') -> list of file paths

This is intentionally simple and deterministic (no LLM). It only answers queries by searching the DB.
"""
import re
from pathlib import Path
from typing import List


def parse_query(q: str):
    """Parse a simple Alfred query string.

    Recognises patterns such as "list images of <name>", "show docs for <name>",
    or a bare name (treated as list images of <name>). Returns a dict with
    keys: action, type, person, where action is 'list' or 'unknown'.
    """
    q = q.strip()
    # simple patterns: "list images of <name>", "show docs of <name>", "list files of <name>"
    m = re.match(r"(?i)\s*(list|show)\s+(images|docs|files|documents|pdfs|pictures)\s+(?:of|for)\s+(.+)", q)
    if m:
        action = m.group(1).lower()
        typ = m.group(2).lower()
        person = m.group(3).strip()
        if typ in {'docs', 'documents', 'pdfs'}:
            typ = 'documents'
        if typ in {'pictures'}:
            typ = 'images'
        return {'action': 'list', 'type': typ, 'person': person}
    # fallback: if it is just a person name, list images
    if q and len(q.split()) <= 4:
        return {'action': 'list', 'type': 'images', 'person': q}
    return {'action': 'unknown'}


def list_files_for_person(db_path: str | Path, person: str, typ: str = 'images') -> List[str]:
    """Return a list of file paths that show matches for the given person.

    typ: 'images' or 'documents' or 'all'
    """
    from ..db.init_db import init_db, get_session
    from ..db.models import FaceMatch, EvidenceFile
    init_db(db_path)
    session = get_session()
    # Find face_matches by subject name
    q = session.query(FaceMatch).filter(FaceMatch.subject == person)
    sources = set()
    for fm in q.all():
        # resolve source path
        sources.add(fm.source)
    out = []
    image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.tiff', '.bmp'}
    doc_exts = {'.pdf', '.txt', '.docx', '.doc'}
    for s in sorted(sources):
        if typ == 'all':
            out.append(s)
        elif typ == 'images' and Path(s).suffix.lower() in image_exts:
            out.append(s)
        elif typ == 'documents' and Path(s).suffix.lower() in doc_exts:
            out.append(s)
    return out
