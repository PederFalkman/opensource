"""Fast offline contract checks for WEB-09 browser choice."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "web09_browser_smoke", APP / "browser_worker_smoke.py"
)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


@pytest.mark.parametrize("engine", ["chromium", "firefox", "webkit"])
def test_browser_engine_selection_reaches_wheel_validation(
    tmp_path: Path, engine: str
) -> None:
    with pytest.raises(ValueError, match="locally built"):
        module.run(tmp_path / "missing.whl", browser_name=engine)


def test_unsupported_browser_fails_before_optional_browser_import(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="Browser must be"):
        module.run(tmp_path / "missing.whl", browser_name="chrome-beta")


def test_invalid_browser_cli_fails_closed() -> None:
    with pytest.raises(SystemExit) as exc:
        module.main([
            "--wheel", "/not-a-wheel.whl", "--browser", "unsupported"
        ])
    assert exc.value.code == 2
