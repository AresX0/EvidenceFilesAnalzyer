import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from case_agent.db.init_db import init_db, get_session
from case_agent.db.models import EvidenceFile, Entity, Transcription, Event
from case_agent.pipelines.timeline_builder import build_timeline


def test_build_timeline_from_date_entity(tmp_path):
    db = tmp_path / "test.db"
    init_db(str(db))
    session = get_session()

    ef = EvidenceFile(path=str(tmp_path / "doc.txt"), size=0, mtime=None, sha256="aaa"
                      )
    session.add(ef)
    session.commit()

    ent_date = Entity(file_id=ef.id, entity_type='DATE', text='2025-01-01', span='0-10', provenance={'sha256': ef.sha256, 'path': ef.path, 'page':1}, confidence='high')
    ent_person = Entity(file_id=ef.id, entity_type='PERSON', text='Alice', span='11-16', provenance={'sha256': ef.sha256, 'path': ef.path, 'page':1}, confidence='high')
    session.add_all([ent_date, ent_person])
    session.commit()

    events = build_timeline(db_path=str(db))
    assert any('2025-01-01' in (e.get('timestamp') or '') or 'inferred:2025-01-01' in (e.get('timestamp') or '') for e in events)
    # ensure person mention was attached to at least one event description
    assert any('Alice' in (e.get('description') or '') for e in events)


def test_build_timeline_from_transcription(tmp_path):
    db = tmp_path / "test2.db"
    init_db(str(db))
    session = get_session()

    ef = EvidenceFile(path=str(tmp_path / "video.mp4"), size=0, mtime=None, sha256="bbb")
    session.add(ef)
    session.commit()

    t = Transcription(file_id=ef.id, text='Meeting on 2025-12-31 at 10:00 discuss time.', segments=[{"start":0, "end":1, "text": 'Meeting at 10:00'}], provenance={'sha256': ef.sha256, 'path': ef.path})
    session.add(t)
    session.commit()

    events = build_timeline(db_path=str(db))
    # should find the numeric time mention
    assert any('10:00' in (e.get('timestamp') or '') or '10:00' in (e.get('description') or '') for e in events)
    # should have an event referencing the file path
    assert any(ef.path in (e.get('provenance', {}).get('path') or '') for e in events)
