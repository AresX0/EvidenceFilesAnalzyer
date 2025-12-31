import sqlite3
from pathlib import Path
import tempfile

from case_agent.pipelines import face_search
from case_agent.reports import generate_extended_report


def test_persist_labeled_results_and_report(tmp_path):
    db = tmp_path / 'test.db'
    res = {
        'source': 'probe.jpg',
        'subject_matches': [
            {'subject': 'Alice', 'best_distance': 0.1, 'matches': [{'path': 'gallery/A1.jpg', 'distance': 0.1}]},
            {'subject': 'Bob', 'best_distance': 0.5, 'matches': [{'path': 'gallery/B1.jpg', 'distance': 0.5}]}
        ]
    }
    face_search._persist_results(str(db), res)
    # confirm table exists and has rows
    conn = sqlite3.connect(str(db))
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM face_matches")
    cnt = cur.fetchone()[0]
    conn.close()
    assert cnt == 2

    # Also check via SQLAlchemy model
    from case_agent.db.init_db import init_db, get_session
    from case_agent.db.models import FaceMatch
    init_db(str(db))
    session = get_session()
    assert session.query(FaceMatch).count() == 2

    # confirm report picks up face_matches
    report = generate_extended_report(str(db))
    assert 'face_matches' in report
    # There should be two distinct gallery entries
    assert any(fm['gallery_path'] == 'gallery/A1.jpg' for fm in report['face_matches'])
    assert any(fm['gallery_path'] == 'gallery/B1.jpg' for fm in report['face_matches'])


def test_persist_unlabeled_results(tmp_path):
    db = tmp_path / 'test2.db'
    res = {'source': 'img.jpg', 'results': [{'face_bbox': {'top': 1}, 'matches': [{'gallery_path': 'g.jpg', 'distance': 0.2}]}]}
    face_search._persist_results(str(db), res)
    conn = sqlite3.connect(str(db))
    cur = conn.cursor()
    cur.execute("SELECT source, gallery_path FROM face_matches")
    rows = cur.fetchall()
    conn.close()
    assert rows[0][0] == 'img.jpg'
    assert rows[0][1] == 'g.jpg'