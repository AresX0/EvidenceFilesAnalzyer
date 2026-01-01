def test_gui_importable():
    # ensure GUI module can be imported and load report without opening
    from case_agent.gui.app import load_report
    rpt = load_report()
    assert 'people' in rpt
    assert isinstance(rpt.get('people'), list)
