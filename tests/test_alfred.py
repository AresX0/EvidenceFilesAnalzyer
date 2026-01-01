from case_agent.agent.alfred import parse_query, list_files_for_person
from case_agent.db.init_db import init_db, get_session
from case_agent.db.models import FaceMatch, EvidenceFile
import tempfile
from pathlib import Path


def test_parse_query():
    assert parse_query('list images of Donald Trump')['person'] == 'Donald Trump'
    assert parse_query('show docs for Alice')['type'] == 'documents'
    assert parse_query('John Doe')['type'] == 'images'


def test_list_files_for_person(tmp_path):
    db = tmp_path / 'test.db'
    init_db(db)
    s = get_session()
    # insert evidence files and face matches
    ef1 = EvidenceFile(path=str(tmp_path / 'img1.jpg'), size=0, mtime=None, sha256='s1')
    ef2 = EvidenceFile(path=str(tmp_path / 'doc1.pdf'), size=0, mtime=None, sha256='s2')
    s.add(ef1); s.add(ef2); s.commit()
    fm1 = FaceMatch(source=str(tmp_path / 'img1.jpg'), probe_bbox=None, subject='Donald Trump', gallery_path=None, distance=0.1)
    fm2 = FaceMatch(source=str(tmp_path / 'doc1.pdf'), probe_bbox=None, subject='Donald Trump', gallery_path=None, distance=0.2)
    s.add(fm1); s.add(fm2); s.commit()

    imgs = list_files_for_person(db, 'Donald Trump', typ='images')
    docs = list_files_for_person(db, 'Donald Trump', typ='documents')
    assert str(tmp_path / 'img1.jpg') in imgs
    assert str(tmp_path / 'doc1.pdf') in docs
