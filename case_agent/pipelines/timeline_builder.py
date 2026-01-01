"""Build structured events from entities and transcriptions.

Behavior:
- Create events from explicit DATE entities (high priority)
- Link PERSON/ORG entities to events when they co-occur with dates
- Create media events when transcriptions contain explicit time references
- All events persist provenance and indicate if timestamps are inferred
- Confidence propagates from entity confidence heuristics
"""
from pathlib import Path
import logging
import re
from ..db.init_db import init_db, get_session
from ..db.models import Event, EvidenceFile

logger = logging.getLogger("case_agent.timeline_builder")

# Simple ISO date pattern and common US/EU numeric dates
ISO_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
NUMERIC_DATE_RE = re.compile(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b")
TIME_HMS_RE = re.compile(r"\b(\d{1,2}:\d{2}(?::\d{2})?)\b")


def _make_event(session, description: str, timestamp: str | None, provenance: dict, confidence: str = "low"):
    ev = Event(description=description, timestamp=timestamp or "inferred:unknown", provenance=provenance)
    session.add(ev)
    session.flush()  # assign id
    ev_dict = {"id": ev.id, "description": ev.description, "timestamp": ev.timestamp, "provenance": ev.provenance}
    logger.debug("Created event %s (timestamp=%s)", ev.id, timestamp)
    return ev_dict


def build_timeline(db_path=None):
    init_db(db_path) if db_path is not None else init_db()
    session = get_session()
    from ..db.models import Entity, Transcription

    events = []

    # 1) Create events from DATE entities — explicit timestamps
    date_entities = session.query(Entity).filter_by(entity_type="DATE").all()
    for d in date_entities:
        prov = d.provenance or {}
        ts = d.text.strip()
        # Decide if timestamp looks explicit (ISO) or inferred (other formats)
        inferred = not bool(ISO_DATE_RE.search(ts))
        description = f"Mention of date: {ts}"
        ev_dict = _make_event(session, description, ts if not inferred else f"inferred:{ts}", prov, confidence=getattr(d, 'confidence', 'low'))
        events.append(ev_dict)

        # Link nearby PERSON/ORG entities (same file and page) as participants
        others = session.query(Entity).filter(Entity.file_id == d.file_id).all()
        # Since we returned dicts above, we need to update the persisted Event row if we append linked info
        linked_notes = []
        for o in others:
            if o.id == d.id:
                continue
            if o.provenance.get('page') == d.provenance.get('page'):
                linked_notes.append(f"{o.entity_type}: {o.text}")
        if linked_notes:
            # fetch the ORM event and update description for auditability
            from sqlalchemy import select
            ev_row = session.execute(select(Event).where(Event.id == ev_dict['id'])).scalar_one()
            ev_row.description += '; ' + '; '.join(linked_notes)
            session.flush()
            # update the dict to include linked notes
            ev_dict['description'] = ev_row.description
            logger.debug('Linked entities to event %s', ev_row.id)

    # 2) Create events from transcriptions where timestamp or explicit mentions exist
    transcriptions = session.query(Transcription).all()
    for t in transcriptions:
        prov = t.provenance or {}
        text = (t.text or "").strip()
        if not text and not t.segments:
            continue
        # If transcription contains ISO dates or numeric dates, create event(s)
        matches = ISO_DATE_RE.findall(text) + NUMERIC_DATE_RE.findall(text)
        if matches:
            for m in matches:
                ev = _make_event(session, f"Transcription mention: {m}", f"inferred:{m}", prov)
                events.append(ev)
                continue
        # Check for time-of-day mentions in segments and create a media event
        for seg in t.segments or []:
            seg_text = seg.get('text', '')
            time_m = TIME_HMS_RE.search(seg_text)
            if time_m:
                ev = _make_event(session, f"Media mention at {time_m.group(1)}: {seg_text}", f"inferred:time:{time_m.group(1)}", prov)
                events.append(ev)
                break
        # If there are no explicit matches, create a low-confidence event that something was said
        if not matches and not any(TIME_HMS_RE.search(s.get('text','')) for s in (t.segments or [])):
            ev = _make_event(session, f"Transcription for file {prov.get('path')}", None, prov)
            events.append(ev)

    try:
        session.commit()
    except Exception as e:
        logger.exception("Failed to commit events: %s", e)
    logger.info("Built %d events", len(events))
    return events


if __name__ == "__main__":
    build_timeline()