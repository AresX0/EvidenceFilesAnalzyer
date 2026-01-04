import threading
import time

import pytest
from werkzeug.serving import make_server

from case_agent.agent.agent import CaseAgent
from case_agent.api import create_app


@pytest.fixture()
def server_and_port(tmp_path):
    db_file = tmp_path / "test_integration.db"
    db_path = str(db_file)
    # initialize DB via CaseAgent
    agent = CaseAgent(db_path=db_path)
    # populate sample data for integration tests
    from case_agent.db.models import Entity, EvidenceFile, ExtractedText, FaceMatch

    s = agent.session
    f = EvidenceFile(path="/tmp/fileA.txt", sha256="deadbeef", size=123)
    s.add(f)
    s.commit()

    et = ExtractedText(
        file_id=f.id,
        page=1,
        text="Alice travelled to Paris.",
        provenance={"sha256": f.sha256, "path": f.path, "page": 1},
    )
    s.add(et)
    ent = Entity(
        file_id=f.id,
        entity_type="PERSON",
        text="Alice",
        provenance={"sha256": f.sha256, "path": f.path, "page": 1},
        confidence="high",
    )
    s.add(ent)
    fm = FaceMatch(
        source=str(f.path),
        subject="Bob",
        gallery_path="/gallery/bob1.jpg",
        distance=0.4,
    )
    s.add(fm)
    s.commit()

    app = create_app(db_path=db_path)
    srv = make_server("127.0.0.1", 0, app)
    port = srv.server_port
    thread = threading.Thread(target=srv.serve_forever)
    thread.daemon = True
    thread.start()

    # wait briefly for server to be ready
    time.sleep(0.1)
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        try:
            srv.shutdown()
        except Exception:
            pass
        thread.join(timeout=2)
