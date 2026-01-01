import pytest

try:
    import tkinter as tk
except Exception:
    tk = None


def test_handle_alfred_query_updates_virtual_grid(monkeypatch, tmp_path):
    if tk is None:
        pytest.skip('Tk not available')

    # Create a fake root and virtual grid
    root = tk.Tk()
    # create a dummy vg with set_person capture
    class DummyVG:
        def __init__(self):
            self.last = None
        def set_person(self, person):
            self.last = person

    vg = DummyVG()
    setattr(root, '_virtual_grid', vg)
    # Ensure tk._default_root points to our root
    tk._default_root = root

    # Monkeypatch DB-backed list_files_for_person to return predictable result
    from case_agent.agent import alfred
    monkeypatch.setattr(alfred, 'list_files_for_person', lambda db, person, typ='images': ['a.jpg', 'b.jpg'])

    # Import the handler and call it
    from case_agent.gui.app import handle_alfred_query
    handle_alfred_query('list images of John Doe')

    assert vg.last is not None
    assert vg.last['person'] == 'John Doe'
    assert vg.last['files'] == ['a.jpg', 'b.jpg']

    # cleanup
    try:
        root.destroy()
    except Exception:
        pass
