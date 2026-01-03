"""Deterministic entity extraction using spaCy when available, otherwise a regex fallback.

This module avoids LLMs and uses only deterministic methods.
"""

import logging
import re
from pathlib import Path

from ..db.init_db import get_session, init_db
from ..db.models import Entity, EvidenceFile

logger = logging.getLogger("case_agent.entity_extract")

try:
    import spacy

    nlp = spacy.load("en_core_web_sm")
except Exception:
    spacy = None
    nlp = None

DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})\b")


def extract_entities_for_file(path: Path, db_path=None):
    init_db(db_path) if db_path is not None else init_db()
    session = get_session()
    file_row = session.query(EvidenceFile).filter_by(path=str(path)).first()
    if not file_row:
        logger.error("File %s not found in DB; run hash_inventory first", path)
        return []
    # Gather text for this file (prefer ExtractedText entries)
    from ..db.models import ExtractedText

    blocks = session.query(ExtractedText).filter_by(file_id=file_row.id).all()
    if not blocks:
        logger.warning("No extracted text for %s; run text_extract", path)
        return []
    entities = []
    for block in blocks:
        text = block.text or ""
        provenance = {
            "sha256": file_row.sha256,
            "path": file_row.path,
            "page": block.page,
        }
        seen = set()
        if nlp:
            try:
                max_len = getattr(nlp, "max_length", 1000000)
                if len(text) > max_len:
                    logger.info(
                        "Text length %d exceeds spaCy max_length %d; chunking",
                        len(text),
                        max_len,
                    )
                    # Use a chunk size safely under the spaCy max_length
                    chunk_size = max_len // 2 if max_len > 1000 else max_len
                    offset = 0
                    while offset < len(text):
                        chunk = text[offset : offset + chunk_size]
                        try:
                            doc = nlp(chunk)
                        except Exception as e:
                            logger.exception(
                                "spaCy chunk NER failed at offset %d for %s: %s",
                                offset,
                                path,
                                e,
                            )
                            # Fallback to regex heuristics for this chunk
                            for m in DATE_RE.finditer(chunk):
                                key = (
                                    "DATE",
                                    m.group(0),
                                    block.page,
                                    m.start() + offset,
                                )
                                if key in seen:
                                    continue
                                seen.add(key)
                                e = Entity(
                                    file_id=file_row.id,
                                    entity_type="DATE",
                                    text=m.group(0),
                                    span=f"{m.start() + offset}-{m.end() + offset}",
                                    provenance=provenance,
                                    confidence="medium",
                                )
                                session.add(e)
                                entities.append(
                                    {
                                        "entity_type": e.entity_type,
                                        "text": e.text,
                                        "confidence": e.confidence,
                                        "provenance": e.provenance,
                                    }
                                )

                            for m in re.finditer(
                                r"\b([A-Z][A-Za-z0-9&'\-\.\s]{2,}?(?:\s+(?:Inc|Ltd|LLC|Corp|Co|Company|Corporation)))\b",
                                chunk,
                            ):
                                org = m.group(1).strip()
                                key = ("ORG", org, block.page, m.start() + offset)
                                if key in seen:
                                    continue
                                seen.add(key)
                                e = Entity(
                                    file_id=file_row.id,
                                    entity_type="ORG",
                                    text=org,
                                    span=f"{m.start() + offset}-{m.end() + offset}",
                                    provenance=provenance,
                                    confidence="medium",
                                )
                                session.add(e)
                                entities.append(
                                    {
                                        "entity_type": e.entity_type,
                                        "text": e.text,
                                        "confidence": e.confidence,
                                        "provenance": e.provenance,
                                    }
                                )

                            for m in re.finditer(
                                r"\b([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,})\b", chunk
                            ):
                                name = m.group(1)
                                key = ("PERSON", name, block.page, m.start() + offset)
                                if key in seen:
                                    continue
                                seen.add(key)
                                e = Entity(
                                    file_id=file_row.id,
                                    entity_type="PERSON",
                                    text=name,
                                    span=f"{m.start() + offset}-{m.end() + offset}",
                                    provenance=provenance,
                                    confidence="low",
                                )
                                session.add(e)
                                entities.append(
                                    {
                                        "entity_type": e.entity_type,
                                        "text": e.text,
                                        "confidence": e.confidence,
                                        "provenance": e.provenance,
                                    }
                                )
                        else:
                            for ent in doc.ents:
                                if ent.label_ in {
                                    "PERSON",
                                    "ORG",
                                    "DATE",
                                    "TIME",
                                    "GPE",
                                }:
                                    key = (
                                        ent.label_,
                                        ent.text,
                                        block.page,
                                        ent.start_char + offset,
                                    )
                                    if key in seen:
                                        continue
                                    seen.add(key)
                                    e = Entity(
                                        file_id=file_row.id,
                                        entity_type=ent.label_,
                                        text=ent.text.strip(),
                                        span=f"{ent.start_char + offset}-{ent.end_char + offset}",
                                        provenance=provenance,
                                        confidence="high",
                                    )
                                    session.add(e)
                                    entities.append(
                                        {
                                            "entity_type": e.entity_type,
                                            "text": e.text,
                                            "confidence": e.confidence,
                                            "provenance": e.provenance,
                                        }
                                    )
                        offset += chunk_size
                    # commit after processing all chunks for this block
                    session.commit()
                else:
                    doc = nlp(text)
                    for ent in doc.ents:
                        if ent.label_ in {"PERSON", "ORG", "DATE", "TIME", "GPE"}:
                            key = (ent.label_, ent.text, block.page)
                            if key in seen:
                                continue
                            seen.add(key)
                            e = Entity(
                                file_id=file_row.id,
                                entity_type=ent.label_,
                                text=ent.text.strip(),
                                span=f"{ent.start_char}-{ent.end_char}",
                                provenance=provenance,
                                confidence="high",
                            )
                            session.add(e)
                            entities.append(
                                {
                                    "entity_type": e.entity_type,
                                    "text": e.text,
                                    "confidence": e.confidence,
                                    "provenance": e.provenance,
                                }
                            )
                    session.commit()
            except Exception as e:
                logger.exception("spaCy NER failed for %s: %s", path, e)
                logger.info("Falling back to regex entity extraction for %s", path)
                # fall through to regex fallback below
        else:
            # Regex-based date extraction as fallback (medium confidence)
            for m in DATE_RE.finditer(text):
                key = ("DATE", m.group(0), block.page)
                if key in seen:
                    continue
                seen.add(key)
                e = Entity(
                    file_id=file_row.id,
                    entity_type="DATE",
                    text=m.group(0),
                    span=f"{m.start()}-{m.end()}",
                    provenance=provenance,
                    confidence="medium",
                )
                session.add(e)
                entities.append(
                    {
                        "entity_type": e.entity_type,
                        "text": e.text,
                        "confidence": e.confidence,
                        "provenance": e.provenance,
                    }
                )

            # Organization heuristics (Inc, Ltd, Corp, LLC)
            for m in re.finditer(
                r"\b([A-Z][A-Za-z0-9&'\-\.\s]{2,}?(?:\s+(?:Inc|Ltd|LLC|Corp|Co|Company|Corporation)))\b",
                text,
            ):
                org = m.group(1).strip()
                key = ("ORG", org, block.page)
                if key in seen:
                    continue
                seen.add(key)
                e = Entity(
                    file_id=file_row.id,
                    entity_type="ORG",
                    text=org,
                    span=f"{m.start()}-{m.end()}",
                    provenance=provenance,
                    confidence="medium",
                )
                session.add(e)
                entities.append(
                    {
                        "entity_type": e.entity_type,
                        "text": e.text,
                        "confidence": e.confidence,
                        "provenance": e.provenance,
                    }
                )

            # Very conservative person detection: two capitalized words
            for m in re.finditer(r"\b([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,})\b", text):
                name = m.group(1)
                key = ("PERSON", name, block.page)
                if key in seen:
                    continue
                seen.add(key)
                e = Entity(
                    file_id=file_row.id,
                    entity_type="PERSON",
                    text=name,
                    span=f"{m.start()}-{m.end()}",
                    provenance=provenance,
                    confidence="low",
                )
                session.add(e)
                entities.append(
                    {
                        "entity_type": e.entity_type,
                        "text": e.text,
                        "confidence": e.confidence,
                        "provenance": e.provenance,
                    }
                )
    session.commit()
    logger.info("Extracted %d entities for %s", len(entities), path)
    return entities


def extract_entities_from_transcription(transcription_id: int, db_path=None):
    """Extract entities from a Transcription row and persist them as Entity rows.

    This allows audio/video transcriptions to be searched like textual files.
    """
    init_db(db_path) if db_path is not None else init_db()
    session = get_session()
    from ..db.models import EvidenceFile, Transcription

    t = session.query(Transcription).filter_by(id=transcription_id).first()
    if not t:
        logger.error("Transcription id %s not found", transcription_id)
        return []
    file_row = session.query(EvidenceFile).filter_by(id=t.file_id).first()
    if not file_row:
        logger.error("File for transcription %s not found", transcription_id)
        return []

    text = t.text or ""
    provenance = {
        "sha256": getattr(file_row, "sha256", None),
        "path": getattr(file_row, "path", None),
        "transcription_id": t.id,
    }
    entities = []
    seen = set()
    if nlp:
        try:
            doc = nlp(text)
            for ent in doc.ents:
                if ent.label_ in {"PERSON", "ORG", "DATE", "TIME", "GPE"}:
                    key = (ent.label_, ent.text)
                    if key in seen:
                        continue
                    seen.add(key)
                    e = Entity(
                        file_id=file_row.id,
                        entity_type=ent.label_,
                        text=ent.text.strip(),
                        span=f"{ent.start_char}-{ent.end_char}",
                        provenance=provenance,
                        confidence="high",
                    )
                    session.add(e)
                    entities.append(
                        {
                            "entity_type": e.entity_type,
                            "text": e.text,
                            "confidence": e.confidence,
                            "provenance": e.provenance,
                        }
                    )
            session.commit()
        except Exception:
            logger.exception(
                "spaCy NER failed for transcription %s; falling back to regex",
                transcription_id,
            )
    # fallback regex extraction similar to above
    if not entities:
        for m in DATE_RE.finditer(text):
            key = ("DATE", m.group(0))
            if key in seen:
                continue
            seen.add(key)
            e = Entity(
                file_id=file_row.id,
                entity_type="DATE",
                text=m.group(0),
                span=f"{m.start()}-{m.end()}",
                provenance=provenance,
                confidence="medium",
            )
            session.add(e)
            entities.append(
                {
                    "entity_type": e.entity_type,
                    "text": e.text,
                    "confidence": e.confidence,
                    "provenance": e.provenance,
                }
            )
        for m in re.finditer(
            r"\b([A-Z][A-Za-z0-9&'\-\.\s]{2,}?(?:\s+(?:Inc|Ltd|LLC|Corp|Co|Company|Corporation)))\b",
            text,
        ):
            org = m.group(1).strip()
            key = ("ORG", org)
            if key in seen:
                continue
            seen.add(key)
            e = Entity(
                file_id=file_row.id,
                entity_type="ORG",
                text=org,
                span=f"{m.start()}-{m.end()}",
                provenance=provenance,
                confidence="medium",
            )
            session.add(e)
            entities.append(
                {
                    "entity_type": e.entity_type,
                    "text": e.text,
                    "confidence": e.confidence,
                    "provenance": e.provenance,
                }
            )
        for m in re.finditer(r"\b([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,})\b", text):
            name = m.group(1)
            key = ("PERSON", name)
            if key in seen:
                continue
            seen.add(key)
            e = Entity(
                file_id=file_row.id,
                entity_type="PERSON",
                text=name,
                span=f"{m.start()}-{m.end()}",
                provenance=provenance,
                confidence="low",
            )
            session.add(e)
            entities.append(
                {
                    "entity_type": e.entity_type,
                    "text": e.text,
                    "confidence": e.confidence,
                    "provenance": e.provenance,
                }
            )
        session.commit()
    logger.info(
        "Extracted %d entities from transcription %s", len(entities), transcription_id
    )
    return entities


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract entities deterministically from extracted text"
    )
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args()
    for p in args.paths:
        extract_entities_for_file(Path(p))
