from case_agent import config
from pathlib import Path
import json

def test_save_and_load(tmp_path, monkeypatch):
    # Use a temp config path by monkeypatching module variable
    cfg_path = tmp_path / 'case_agent_config.json'
    monkeypatch.setattr(config, '_CONFIG_PATH', cfg_path)
    config.PDF_VIEWER = 'C:/Test/Viewer.exe'
    ok = config.save_user_config()
    assert ok
    # reload module-level variable by calling loader
    config._load_user_config()
    assert config.PDF_VIEWER == 'C:/Test/Viewer.exe'
    content = json.loads(cfg_path.read_text(encoding='utf-8'))
    assert content['PDF_VIEWER'] == 'C:/Test/Viewer.exe'
