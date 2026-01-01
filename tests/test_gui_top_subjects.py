import json
import pytest
from PIL import Image

pytest.importorskip('tkinter')


def test_gui_shows_top_subjects(monkeypatch, tmp_path):
    img = tmp_path / 'img.jpg'
    Image.new('RGB', (200, 200), color=(12, 34, 56)).save(img)
    rpt = {'people': [{'person': 'S1', 'files': [str(img)], 'file_count': 1}], 'top_subjects': [{'subject': 'S1', 'count': 1}]}
    rpt_path = tmp_path / 'report.json'
    rpt_path.write_text(json.dumps(rpt), encoding='utf-8')

    import tkinter as tk
    orig_Tk = tk.Tk
    container = {}

    def fake_Tk(*args, **kwargs):
        inst = orig_Tk(*args, **kwargs)
        container['root'] = inst
        return inst

    monkeypatch.setattr('tkinter.Tk.mainloop', lambda self: None, raising=False)
    monkeypatch.setattr(tk, 'Tk', fake_Tk)

    from case_agent.gui.app import run_gui
    run_gui(report_path=rpt_path)
    root = container['root']
    assert hasattr(root, 'top_subjects_frame')
    # ensure there is at least one Listbox in the frame
    found = False
    for c in root.top_subjects_frame.winfo_children():
        try:
            if c.winfo_class() == 'Listbox':
                if c.size() >= 1:
                    found = True
                    break
        except Exception:
            continue
    assert found, 'Top subjects list not populated'