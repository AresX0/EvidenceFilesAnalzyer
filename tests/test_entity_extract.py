import sys
from pathlib import Path
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from case_agent.db.init_db import init_db, get_session
from case_agent.db.models import EvidenceFile, ExtractedText, Entity
from case_agent.pipelines.entity_extract import extract_entities_for_file


def test_entity_extraction_with_spacy(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    init_db(str(db))
    session = get_session()

    # Create evidence and extracted text
    ef = EvidenceFile(path=str(tmp_path / "doc.txt"), size=0, mtime=None, sha256="deadbeef")
    session.add(ef)
    session.commit()

    et = ExtractedText(file_id=ef.id, page=1, text="John Doe met with Acme Corp on 2023-01-02 in Seattle.", provenance={"sha256": ef.sha256, "path": ef.path})
    session.add(et)
    session.commit()

    # Run entity extraction (uses actual spaCy if available)
    ents = extract_entities_for_file(Path(ef.path), db_path=str(db))
    assert any(e['entity_type'] == 'PERSON' and 'John' in e['text'] for e in ents)
    assert any(e['entity_type'] == 'ORG' and 'Acme' in e['text'] for e in ents)
    assert any(e['entity_type'] == 'DATE' and '2023' in e['text'] for e in ents)


def test_entity_extraction_fallback_no_spacy(tmp_path, monkeypatch):
    # Force no spacy available by monkeypatching the module variables
    import importlib
    import case_agent.pipelines.entity_extract as ent_mod
    monkeypatch.setattr(ent_mod, 'nlp', None)

    db = tmp_path / "test2.db"
    init_db(str(db))
    session = get_session()

    ef = EvidenceFile(path=str(tmp_path / "doc2.txt"), size=0, mtime=None, sha256="cafebabe")
    session.add(ef)
    session.commit()

    et = ExtractedText(file_id=ef.id, page=1, text="Jane Smith visited Example Inc on 2024-05-06.", provenance={"sha256": ef.sha256, "path": ef.path})
    session.add(et)
    session.commit()

    ents = extract_entities_for_file(Path(ef.path), db_path=str(db))
    # regex fallback should find ORG and PERSON and DATE
    assert any(e['entity_type'] == 'ORG' and 'Example' in e['text'] for e in ents)
    assert any(e['entity_type'] == 'PERSON' and 'Jane' in e['text'] for e in ents)
    assert any(e['entity_type'] == 'DATE' and '2024' in e['text'] for e in ents)
