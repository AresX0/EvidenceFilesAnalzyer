import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from case_agent.db.init_db import init_db, get_session
from case_agent.db.models import EvidenceFile, ExtractedText
from case_agent.agent.agent import CaseAgent


class FakeResp:
    def __init__(self, text):
        self._text = text
        self.status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return json.loads(self._text)

    @property
    def text(self):
        return self._text


def test_summarize_with_ollama_parses_json(monkeypatch, tmp_path):
    db = tmp_path / "test.db"
    init_db(str(db))
    session = get_session()

    ef = EvidenceFile(path=str(tmp_path / "doc.txt"), size=0, mtime=None, sha256="s1")
    session.add(ef)
    session.commit()

    et = ExtractedText(file_id=ef.id, page=1, text='Alice met Bob on 2025-01-01', provenance={'sha256': ef.sha256, 'path': ef.path})
    session.add(et)
    session.commit()

    agent = CaseAgent(db_path=str(db))

    fake_json = json.dumps({"facts": [{"text": "Alice met Bob", "sources": [{"sha256": "s1", "path": ef.path}], "confidence": "high"}]})

    def fake_post(url, json=None, timeout=None):
        return FakeResp(fake_json)

    monkeypatch.setattr('requests.post', fake_post)

    res = agent.summarize_with_ollama('Who met Bob?')
    assert 'facts' in res
    assert res['facts'][0]['confidence'] == 'high'


def test_summarize_with_ollama_handles_nonjson(monkeypatch, tmp_path):
    db = tmp_path / "test2.db"
    init_db(str(db))
    session = get_session()

    ef = EvidenceFile(path=str(tmp_path / "doc2.txt"), size=0, mtime=None, sha256="s2")
    session.add(ef)
    session.commit()

    et = ExtractedText(file_id=ef.id, page=1, text='No dates here', provenance={'sha256': ef.sha256, 'path': ef.path})
    session.add(et)
    session.commit()

    agent = CaseAgent(db_path=str(db))

    fake_text = 'Some commentary\n{"facts":[{"text":"something","sources":[{"sha256":"s2","path":"path"}],"confidence":"low"}]}'

    def fake_post(url, json=None, timeout=None):
        return FakeResp(fake_text)

    monkeypatch.setattr('requests.post', fake_post)

    res = agent.summarize_with_ollama('Any facts?')
    assert 'facts' in res
    assert res['facts'][0]['confidence'] == 'low'
