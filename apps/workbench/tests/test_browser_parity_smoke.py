"""Fast, offline checks of the opt-in real-browser parity harness."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("edk_browser_smoke", HERE / "browser_parity_smoke.py")
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def test_rejects_missing_wheel_before_starting_browser(tmp_path: Path) -> None:
    """No runtime or network activity is needed for invalid wheel inputs."""
    with pytest.raises(ValueError, match="trusted locally built"):
        module.run(tmp_path / "missing.whl")


def test_rejects_oversized_wheel_before_starting_browser(tmp_path: Path) -> None:
    """Reject size violations without importing Playwright or starting a server."""
    wheel = tmp_path / "energydata_kit-0.17.0-py3-none-any.whl"
    with wheel.open("wb") as f:
        f.truncate(module.MAX_WHEEL_BYTES + 1)
    with pytest.raises(ValueError, match="10 MiB"):
        module.run(wheel)


def test_invalid_timeout_is_rejected(tmp_path: Path) -> None:
    """CLI must reject impossible timeouts without starting browser operations."""
    with pytest.raises(SystemExit) as exc:
        module.main(["--wheel", str(tmp_path / "missing.whl"), "--timeout-ms", "0"])
    assert exc.value.code == 2
