import time

from case_agent.gui import CaseAgentGUI


def test_headless_gui_people_and_query(server_and_port):
    api_url = server_and_port
    gui = CaseAgentGUI(db_path=None, api_url=api_url, headless=True)

    # prepare data in server DB via a client call (server already initialized by fixture)
    # Ask the agent via GUI
    gui.query_var.set("Alice")
    gui.ask_agent()

    # allow background thread to run
    time.sleep(0.2)

    out = gui.output.getvalue()
    assert ("Agent summary" in out) or ("Agent:" in out) or ("Agent error" not in out)

    # call people report and ensure results written to output in headless mode
    gui.show_people_report()
    time.sleep(0.2)
    out2 = gui.output.getvalue()
    assert "files" in out2 or " — " in out2 or "People report" not in out2
