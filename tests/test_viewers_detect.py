import builtins
import shutil
import os
from unittest import mock

from case_agent.utils import viewers


def test_detect_pdf_viewer_uses_shutil_which(monkeypatch):
    # make detection deterministic by forcing which to return Sumatra for that name
    monkeypatch.setattr(shutil, 'which', lambda name: r"C:\Program Files\SumatraPDF\SumatraPDF.exe" if name == 'SumatraPDF.exe' else None)
    monkeypatch.setattr('os.name', 'posix', raising=False)
    res = viewers.detect_pdf_viewer()
    assert res is not None
    # just ensure it returns a path-like result (non-empty string) for this deterministic stub
    s = str(res)
    assert len(s) > 0


def test_detect_pdf_viewer_windows_common_paths(monkeypatch):
    # simulate windows
    monkeypatch.setattr(os, 'name', 'nt', raising=False)
    # force common windows location checker to return a fake path (set attr even if absent)
    monkeypatch.setattr(viewers, '_check_common_windows_locations', lambda: r'C:\Program Files\SumatraPDF\SumatraPDF.exe', raising=False)
    # ensure which finds nothing so common locations are used
    monkeypatch.setattr(shutil, 'which', lambda name: None)
    res = viewers.detect_pdf_viewer()
    assert res is not None
    s = str(res)
    assert len(s) > 0