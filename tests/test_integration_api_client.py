import time

from case_agent.agent.client import AgentClient
from case_agent.gui import CaseAgentGUI


def test_agent_client_against_server(server_and_port):
    api_url = server_and_port
    client = AgentClient(api_url=api_url)

    # query
    res = client.answer_query("Alice")
    assert isinstance(res, dict)
    assert ("facts" in res and len(res.get("facts", [])) >= 1) or (
        res.get("message") == "insufficient evidence"
    )

    # people report
    rpt = client.people_report()
    assert isinstance(rpt, dict)
    assert "people" in rpt
    ppl = [p.get("person") for p in rpt.get("people", [])]
    assert any(p in ("Alice", "Bob") for p in ppl)


def test_headless_gui_uses_api(server_and_port):
    api_url = server_and_port
    gui = CaseAgentGUI(db_path=None, api_url=api_url, headless=True)

    # simulate typing a query (set query_var) and invoking ask_agent
    gui.query_var.set("Alice")
    gui.ask_agent()

    # allow background thread to run
    time.sleep(0.2)

    out = gui.output.getvalue()
    assert ("Agent summary" in out) or ("Agent:" in out) or ("Agent error" not in out)

    # call people report; the headless GUI's show_people_report will still create a Toplevel (skipped in tests)
    # but ensure the client call works
    rpt = gui.client.people_report()
    assert "people" in rpt
    assert isinstance(rpt.get("people"), list)
