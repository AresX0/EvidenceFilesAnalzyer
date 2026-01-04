from case_agent.agent.agent import CaseAgent
from case_agent.api import create_app
from case_agent.db.models import Entity, EvidenceFile, ExtractedText, FaceMatch


def setup_sample_data(agent: CaseAgent):
    s = agent.session
    # create a file
    f = EvidenceFile(path="/tmp/file1.txt", sha256="deadbeef", size=123)
    s.add(f)
    s.commit()
    # add extracted text containing a name
    et = ExtractedText(
        file_id=f.id,
        page=1,
        text="Alice went to the market.",
        provenance={"sha256": f.sha256, "path": f.path, "page": 1},
    )
    s.add(et)
    # add entity
    ent = Entity(
        file_id=f.id,
        entity_type="PERSON",
        text="Alice",
        provenance={"sha256": f.sha256, "path": f.path, "page": 1},
        confidence="high",
    )
    s.add(ent)
    # add face match subject
    fm = FaceMatch(
        source=str(f.path),
        subject="Bob",
        gallery_path="/gallery/bob1.jpg",
        distance=0.45,
    )
    s.add(fm)
    s.commit()


def test_agent_find_endpoint(tmp_path):
    db_file = tmp_path / "test_agent.db"
    db_path = str(db_file)
    agent = CaseAgent(db_path=db_path)
    setup_sample_data(agent)

    app = create_app(db_path=db_path)
    client = app.test_client()

    rv = client.get("/agent/find", query_string={"query": "Alice"})
    assert rv.status_code == 200
    data = rv.get_json()
    assert "result" in data
    assert isinstance(data["result"], list)
    assert any("Alice" in (r.get("excerpt") or "") for r in data["result"]) or any(
        r.get("path") for r in data["result"]
    )


def test_reports_people_endpoint(tmp_path):
    db_file = tmp_path / "test_agent2.db"
    db_path = str(db_file)
    agent = CaseAgent(db_path=db_path)
    setup_sample_data(agent)

    app = create_app(db_path=db_path)
    client = app.test_client()

    rv = client.get("/reports/people")
    assert rv.status_code == 200
    data = rv.get_json()
    assert "people" in data
    # should at least have Bob (from face match) or Alice (from entity)
    people = [p.get("person") for p in data.get("people", [])]
    assert any("Alice" == p for p in people) or any("Bob" == p for p in people)
