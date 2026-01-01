import json
from pathlib import Path
import importlib

import case_agent.config as cfg


def test_pdf_viewer_persistence(tmp_path, monkeypatch):
    # backup any existing config file and point cfg to use tmp_path
    cfg_file = Path('case_agent_config.json')
    backup = None
    if cfg_file.exists():
        backup = cfg_file.read_text(encoding='utf-8')
    try:
        cfg.PDF_VIEWER = str(tmp_path / 'dummy.exe')
        cfg.SHOW_TOP_SUBJECTS = True
        cfg.save_user_config()
        data = json.loads(cfg_file.read_text(encoding='utf-8'))
        assert data.get('PDF_VIEWER') == str(tmp_path / 'dummy.exe')
        assert data.get('SHOW_TOP_SUBJECTS') is True
    finally:
        if backup is not None:
            cfg_file.write_text(backup, encoding='utf-8')
        else:
            try:
                cfg_file.unlink()
            except Exception:
                pass