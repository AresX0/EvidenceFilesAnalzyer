import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from case_agent.db.init_db import init_db, get_session
from case_agent.db.models import EvidenceFile, Transcription
from case_agent.agent.agent import CaseAgent


def test_find_media_mentions_matches(tmp_path):
    db = tmp_path / "test.db"
    init_db(str(db))
    session = get_session()

    ef = EvidenceFile(path=str(tmp_path / "video.mp4"), size=0, mtime=None, sha256="abcd")
    session.add(ef)
    session.commit()

    t = Transcription(file_id=ef.id, text="This is a test transcript. Hello world from speaker.", segments=[{"start": 0.0, "end":1.0, "text":"Hello world"}], provenance={"sha256":ef.sha256})
    session.add(t)
    session.commit()

    agent = CaseAgent(db_path=str(db))
    res = agent.find_media_mentions("hello")
    assert isinstance(res, list)
    assert res and res[0].get("file_sha256") == "abcd"
    assert any("hello" in (r.get("excerpt") or "").lower() for r in res)


def test_find_media_mentions_no_match(tmp_path):
    db = tmp_path / "test2.db"
    init_db(str(db))
    session = get_session()

    ef = EvidenceFile(path=str(tmp_path / "audio.wav"), size=0, mtime=None, sha256="zzzz")
    session.add(ef)
    session.commit()

    t = Transcription(file_id=ef.id, text="Nothing interesting here.", segments=[], provenance={"sha256":ef.sha256})
    session.add(t)
    session.commit()

    agent = CaseAgent(db_path=str(db))
    res = agent.find_media_mentions("foobar")
    assert res == [{"message": "insufficient evidence", "confidence": "low"}]
