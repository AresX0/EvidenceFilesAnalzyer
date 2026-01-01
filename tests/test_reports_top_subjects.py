import json
from pathlib import Path
from case_agent.reports import write_report_html

def test_write_report_includes_top_subjects(tmp_path):
    rpt = {
        'counts': {'files': 1},
        'top_subjects': [{'subject': 'Alice', 'count': 5}, {'subject': 'Bob', 'count': 3}],
        'people': []
    }
    out = tmp_path / 'report.html'
    write_report_html(rpt, out)
    txt = out.read_text(encoding='utf-8')
    assert 'Top Subjects' in txt
    assert 'Alice (5)' in txt or 'Alice' in txt
    assert 'Bob (3)' in txt or 'Bob' in txt