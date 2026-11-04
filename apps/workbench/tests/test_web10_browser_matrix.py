"""WEB-10 fast offline tests for the opt-in multi-browser worker harness."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import pytest

APP = Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("web10_browser",APP/"browser_worker_smoke.py")
assert spec and spec.loader
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

@pytest.mark.parametrize("name",["chromium","firefox","webkit"])
def test_browser_accepted(name: str) -> None:
    assert module.validate_browser(name)==name

@pytest.mark.parametrize("name",["Chrome","safari","../firefox","","all"])
def test_unknown_browser_rejected(name: str) -> None:
    with pytest.raises(ValueError,match="Unsupported browser"):
        module.validate_browser(name)

def test_cli_rejects_unsupported_browser_before_install() -> None:
    with pytest.raises(SystemExit) as err:
        module.main(["--wheel","missing.whl","--browser","invalid"])
    assert err.value.code==2

def test_missing_wheel_fails_closed_without_playwright(tmp_path: Path) -> None:
    with pytest.raises(ValueError,match="locally built"):
        module.run(tmp_path/"missing.whl",browser_name="firefox")
