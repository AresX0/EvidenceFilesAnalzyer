import tempfile
from pathlib import Path
from case_agent.db.init_db import init_db, get_session
from case_agent.db.models import EvidenceFile, Transcription, Entity
from case_agent.pipelines.media_extract import persist_transcription, transcribe_whisper_local
from case_agent.pipelines.entity_extract import extract_entities_from_transcription


def test_transcription_entity_extraction(tmp_path):
    db = tmp_path / 'test.db'
    init_db(str(db))
    s = get_session()
    # create a fake file row
    f = EvidenceFile(path=str(tmp_path / 'a.wav'), sha256='deadbeef', size=0)
    s.add(f)
    s.commit()
    # create a transcription record
    t = Transcription(file_id=f.id, text='Donald Trump spoke in New York on 2020-01-01', segments=[], provenance={"sha256": f.sha256, "path": f.path})
    s.add(t)
    s.commit()
    # run entity extraction for transcription
    ents = extract_entities_from_transcription(t.id, db_path=str(db))
    assert any(e['entity_type'] == 'PERSON' for e in ents)
    assert any(e['entity_type'] == 'DATE' for e in ents)
