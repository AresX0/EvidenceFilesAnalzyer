import json
import pytest
from pathlib import Path
from PIL import Image

pytest.importorskip('tkinter')


def test_run_gui_builds_widgets(monkeypatch, tmp_path):
    # create a simple report
    img = tmp_path / 'img.jpg'
    Image.new('RGB', (200, 200), color=(12, 34, 56)).save(img)
    rpt = {'people': [{'person': 'S1', 'files': [str(img)], 'file_count': 1}]}
    rpt_path = tmp_path / 'report.json'
    rpt_path.write_text(json.dumps(rpt), encoding='utf-8')

    import tkinter as tk
    orig_Tk = tk.Tk
    container = {}

    def fake_Tk(*args, **kwargs):
        inst = orig_Tk(*args, **kwargs)
        container['root'] = inst
        return inst

    # monkeypatch mainloop to no-op so test doesn't block
    monkeypatch.setattr('tkinter.Tk.mainloop', lambda self: None, raising=False)
    monkeypatch.setattr(tk, 'Tk', fake_Tk)

    from case_agent.gui.app import run_gui
    # should not raise and should create root in container
    run_gui(report_path=rpt_path)
    assert 'root' in container
    # clean up by destroying the window
    try:
        container['root'].destroy()
    except Exception:
        pass
