import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from case_agent.db.init_db import init_db, get_session
from case_agent.db.models import EvidenceFile, ExtractedText, Transcription
from case_agent.agent.agent import CaseAgent


def test_answer_query_text_match(tmp_path):
    db = tmp_path / "test.db"
    init_db(str(db))
    session = get_session()

    ef = EvidenceFile(path=str(tmp_path / "doc.txt"), size=0, mtime=None, sha256="s1")
    session.add(ef)
    session.commit()

    et = ExtractedText(file_id=ef.id, page=1, text='The suspect code name is "X-123" and was mentioned in the note.', provenance={'sha256': ef.sha256, 'path': ef.path})
    session.add(et)
    session.commit()

    agent = CaseAgent(db_path=str(db))
    res = agent.answer_query('X-123')
    assert 'facts' in res
    assert res['facts'][0]['confidence'] in {'low', 'medium', 'high'}


def test_answer_query_no_match(tmp_path):
    db = tmp_path / "test2.db"
    init_db(str(db))
    session = get_session()

    ef = EvidenceFile(path=str(tmp_path / "doc2.txt"), size=0, mtime=None, sha256="s2")
    session.add(ef)
    session.commit()

    agent = CaseAgent(db_path=str(db))
    res = agent.answer_query('nothing')
    assert res == {"message": "insufficient evidence", "confidence": "low"}
