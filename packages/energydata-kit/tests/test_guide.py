"""Run every code block in ``examples/GUIDE.md`` so the guide stays correct.

Python blocks run in order in one shared namespace, inside a temporary
directory. Bash blocks may only call ``energydata-kit``; each command runs as
``python -m energydata_kit`` and must exit 0 unless the command ends with a
``# exit status: N`` comment. A block preceded by ``<!-- requires: NAME -->``
is skipped (with the rest of the guide still running) when module ``NAME``
is not installed.
"""

from __future__ import annotations

import importlib.util
import re
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

GUIDE = Path(__file__).parent.parent / "examples" / "GUIDE.md"
_FENCE = re.compile(r"(?:<!-- requires: (\w+) -->\n)?```(python|bash)\n(.*?)```", re.DOTALL)
_EXIT = re.compile(r"#\s*exit status:\s*(\d+)\s*$")


def blocks() -> list[tuple[int, str, str, str | None]]:
    text = GUIDE.read_text(encoding="utf-8")
    return [
        (text.count("\n", 0, m.start(2)) + 1, m.group(2), m.group(3), m.group(1))
        for m in _FENCE.finditer(text)
    ]


def commands(code: str) -> list[tuple[list[str], int]]:
    joined = re.sub(r"\\\n\s*", " ", code)
    out = []
    for line in joined.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        exit_match = _EXIT.search(line)
        argv = shlex.split(line, comments=True)
        assert argv[0] == "energydata-kit", f"guide bash blocks may only run energydata-kit: {line}"
        out.append((argv[1:], int(exit_match.group(1)) if exit_match else 0))
    return out


def test_guide_has_code():
    kinds = {kind for _, kind, _, _ in blocks()}
    assert kinds == {"python", "bash"}


def test_guide_runs(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    namespace: dict[str, object] = {"__name__": "guide"}
    for line, kind, code, requires in blocks():
        if requires and importlib.util.find_spec(requires) is None:
            continue
        where = f"{GUIDE.name}:{line}"
        if kind == "python":
            exec(compile(code, where, "exec"), namespace)  # our own docs
            continue
        for argv, expected in commands(code):
            result = subprocess.run(
                [sys.executable, "-m", "energydata_kit", *argv],
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == expected, f"{where}: {argv}\n{result.stderr}"
    capsys.readouterr()


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("energydata-kit report a.csv\n", [(["report", "a.csv"], 0)]),
        (
            "energydata-kit report a.csv \\\n    --freq 1h  # exit status: 1\n",
            [(["report", "a.csv", "--freq", "1h"], 1)],
        ),
        ("# comment\n\nenergydata-kit --version\n", [(["--version"], 0)]),
    ],
)
def test_command_parsing(code, expected):
    assert commands(code) == expected
