import sys
import tempfile
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from case_agent.db.init_db import init_db, get_session
from case_agent.db.models import EvidenceFile, Transcription
from case_agent.pipelines.media_extract import transcribe_whisper_local, persist_transcription


def test_persist_transcription_with_mock_whisper(monkeypatch, tmp_path):
    # Setup a temporary DB
    db_path = tmp_path / "test.db"
    init_db(str(db_path))
    session = get_session()

    # Add a dummy EvidenceFile
    ef = EvidenceFile(path=str(tmp_path / "sample.wav"), size=0, mtime=None, sha256="deadbeef")
    session.add(ef)
    session.commit()

    # Mock a transcription result
    fake_result = {"segments": [{"start": 0.0, "end": 1.0, "text": "Hello world"}], "text": "Hello world"}

    # Persist using helper
    t = persist_transcription(session, ef, fake_result)
    assert t.id is not None
    assert t.text == "Hello world"
    assert isinstance(t.segments, list)
    assert t.provenance["sha256"] == "deadbeef"


def test_transcribe_whisper_local_mock(monkeypatch, tmp_path):
    # Create a fake whisper module
    class FakeModel:
        def transcribe(self, path, verbose=False):
            return {"segments": [{"start": 0, "end": 0.5, "text": "test"}], "text": "test"}

    class FakeWhisper:
        def load_model(self, name):
            return FakeModel()

    import importlib
    import case_agent.pipelines.media_extract as media_extract
    monkeypatch.setattr(media_extract, 'whisper', FakeWhisper())

    # Create a fake audio file path
    audio = tmp_path / "sample.wav"
    audio.write_bytes(b"RIFF....")

    result = transcribe_whisper_local(audio)
    assert result["text"] == "test"
    assert len(result["segments"]) == 1
