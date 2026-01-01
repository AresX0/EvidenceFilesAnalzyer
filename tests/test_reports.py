import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from case_agent.db.init_db import init_db, get_session
from case_agent.db.models import EvidenceFile, ExtractedText, Entity
from case_agent.reports import generate_extended_report


def test_generate_extended_report(tmp_path):
    db = tmp_path / "test.db"
    init_db(str(db))
    session = get_session()

    ef = EvidenceFile(path=str(tmp_path / "doc.txt"), size=0, mtime=None, sha256="aaa")
    session.add(ef)
    session.commit()

    et = ExtractedText(file_id=ef.id, page=1, text='Hello world: 2025-01-01', provenance={'sha256': ef.sha256, 'path': ef.path})
    e1 = Entity(file_id=ef.id, entity_type='DATE', text='2025-01-01', provenance={'sha256': ef.sha256, 'path': ef.path})
    session.add_all([et, e1])
    session.commit()

    r = generate_extended_report(str(db))
    assert 'files' in r
    assert r['counts']['files'] == 1
    assert r['counts']['entities'] == 1
    assert next(iter(r['excerpts'].values()))[0]['excerpt'].startswith('Hello')
