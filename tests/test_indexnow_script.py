from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "submit_indexnow.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("submit_indexnow_for_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_indexnow_payload_uses_root_key_location_and_all_urls():
    module = load_script_module()
    paths = module.build_paths()
    assert len(paths) == 84
    assert len(paths) == len(set(paths))
    payload = module.build_payload(
        "https://chinatraderesolve.com",
        "abcdefgh12345678",
        "chinatraderesolve.com",
        paths,
    )
    assert payload["keyLocation"] == "https://chinatraderesolve.com/abcdefgh12345678.txt"
    assert all(url.startswith("https://chinatraderesolve.com/") for url in payload["urlList"])
    assert "https://chinatraderesolve.com/fr/guides/supplier-not-refunding" in payload["urlList"]
    assert "https://chinatraderesolve.com/sr/guides" in payload["urlList"]


def test_script_bootstraps_project_root_when_run_directly():
    env = os.environ.copy()
    env.pop("PUBLIC_BASE_URL", None)
    env.pop("RENDER_EXTERNAL_URL", None)
    env.pop("INDEXNOW_KEY", None)
    completed = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    output = completed.stdout + completed.stderr
    assert completed.returncode != 0
    assert "Set PUBLIC_BASE_URL or RENDER_EXTERNAL_URL" in output
    assert "No module named 'app'" not in output
