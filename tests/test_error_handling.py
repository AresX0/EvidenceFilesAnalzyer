import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from case_agent.db.init_db import init_db, get_session
from case_agent.db.models import EvidenceFile, ExtractedText
import case_agent.pipelines.text_extract as text_mod


def test_text_extract_handles_exceptions(tmp_path, monkeypatch, caplog):
    db = tmp_path / "test.db"
    init_db(str(db))
    session = get_session()

    ef = EvidenceFile(path=str(tmp_path / "doc.txt"), size=0, mtime=None, sha256="abc")
    session.add(ef)
    session.commit()

    et = ExtractedText(file_id=ef.id, page=1, text="Some text", provenance={"sha256": ef.sha256})
    session.add(et)
    session.commit()

    # Create the actual file so the extractor is invoked
    Path(ef.path).write_text('Dummy content')

    # Monkeypatch the extractor to raise
    monkeypatch.setattr(text_mod, 'extract_text_from_txt', lambda p: (_ for _ in ()).throw(RuntimeError('boom')))

    caplog.clear()
    res = text_mod.extract_for_file(Path(ef.path), db_path=str(db))
    # Should not raise; should return [] or pages (since our fallback returns empty), and error should be logged
    assert res == [] or isinstance(res, list)
    # We accept that an exception was logged
    assert any('exception' in m.lower() or 'failed' in m.lower() for m in caplog.messages)

