from case_agent.gui.app import VirtualThumbGridModel


def test_visible_range_basic():
    m = VirtualThumbGridModel(cols=3, thumb_size=(100, 50), gap=(4, 4))
    files = [f'f{i}.jpg' for i in range(12)]
    m.set_files(files)
    w, h = m.scroll_region()
    assert w > 0 and h > 0
    # simulated total height with some rows
    total_h = h
    # visible top third
    start, end = m.visible_range_from_view(total_h, 0.0, 0.3)
    assert start >= 0 and end >= start
    # full view should include all
    s, e = m.visible_range_from_view(total_h, 0.0, 1.0)
    assert s == 0 and e == len(files)