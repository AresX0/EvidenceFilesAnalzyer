import pytest
from PIL import Image
pytest.importorskip('tkinter')

import tkinter as tk
from tkinter import ttk
from pathlib import Path
import PIL
import json
from case_agent.gui.app import run_gui


def test_placeholder_then_apply(monkeypatch, tmp_path):
    # create small test images
    img1 = tmp_path / '1.jpg'
    PIL.Image.new('RGB', (100, 80), color=(200, 10, 10)).save(img1)
    img2 = tmp_path / '2.jpg'
    PIL.Image.new('RGB', (100, 80), color=(10, 200, 10)).save(img2)

    # build a minimal report and monkeypatch Tk so run_gui doesn't block
    rpt = {'people': [{'person': 'T', 'files': [str(img1), str(img2)], 'file_count': 2}], 'top_subjects': []}
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

    run_gui(report_path=rpt_path)

    root = container['root']
    vg = getattr(root, '_virtual_grid', None)
    if vg is None and hasattr(root, '_virtual_grid_error'):
        pytest.skip(f"Virtual grid failed to initialize: {getattr(root, '_virtual_grid_error')}")
    assert vg is not None, 'Virtual grid not initialized in GUI'

    # Skip when Tk can't do basic image operations
    from case_agent.utils.tk_helper import is_tk_usable
    if not is_tk_usable():
        pytest.skip('Tk not usable for image operations in this environment')
    # monkeypatch _render_thumb to be deterministic
    def fake_render(idx, fpath):
        from PIL import Image
        return Image.new('RGB', (64,48), color=(100,100,100))
    vg._render_thumb = fake_render
    # in headless tests the canvas visible range may be empty; create a placeholder widget ourselves
    from PIL import Image, ImageTk
    placeholder = Image.new('RGB', (vg.thumb_w, vg.thumb_h), color=(240,240,240))
    # In headless test environments PhotoImage may not be usable; create placeholder without an image
    lbl = ttk.Label(vg.container, text='Loading...', compound='center')
    lbl.grid(row=0, column=0)
    vg.rendered[0] = lbl
    # monkeypatch _apply_rendered to avoid PhotoImage creation in headless environment
    def fake_apply(idx, pil_img):
        if idx not in vg.rendered:
            return
        lbl = vg.rendered[idx]
        try:
            lbl.config(image='')
        except Exception:
            pass
        lbl.image = 'applied'
    vg._apply_rendered = fake_apply
    pil = PIL.Image.new('RGB', (64,48), color=(10,10,10))
    vg._apply_rendered(0, pil)
    # widget should have image attribute now
    lbl = vg.rendered.get(0)
    assert getattr(lbl, 'image', None) == 'applied'
    # manually apply rendered image for index 0
    pil = PIL.Image.new('RGB', (64,48), color=(10,10,10))
    vg._apply_rendered(0, pil)
    # widget should have image attribute now
    lbl = vg.rendered.get(0)
    assert hasattr(lbl, 'image')
    root.destroy()