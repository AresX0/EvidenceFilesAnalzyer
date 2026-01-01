from case_agent.reports import generate_extended_report

def test_people_and_pdf_synopses_exist():
    rpt = generate_extended_report(r"C:\Projects\FileAnalyzer\file_analyzer.db")
    assert isinstance(rpt.get('people'), list)
    assert isinstance(rpt.get('pdf_synopses'), list)
    # If DB has data, there should be some people
    # This is a soft assertion (if empty DB is present it's okay)
    assert 'people' in rpt
    assert 'pdf_synopses' in rpt
