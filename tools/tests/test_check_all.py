import importlib.util
import re
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent
REPO = TOOLS.parent

spec = importlib.util.spec_from_file_location("check_all", TOOLS / "check_all.py")
assert spec and spec.loader
ca = importlib.util.module_from_spec(spec)
sys.modules["check_all"] = ca
spec.loader.exec_module(ca)


def _py(code: str) -> list[str]:
    return [sys.executable, "-c", code]


def test_runs_every_check_and_reports_failures(tmp_path):
    checks = [
        ca.Check("ok", _py("print('fine')"), tmp_path),
        ca.Check("broken", _py("import sys; print('boom'); sys.exit(3)"), tmp_path),
        ca.Check("after", _py("pass"), tmp_path),
        ca.Check("info", _py("import sys; sys.exit(1)"), tmp_path, informational=True),
    ]
    outcomes = ca.run(checks, echo=False)
    assert [o.status for o in outcomes] == ["PASS", "FAIL", "PASS", "INFO"]  # keeps going after a failure
    text = ca.summary(outcomes)
    assert "--- broken (exit 3) ---\nboom" in text
    assert text.endswith("1 of 4 checks failed.")


def test_all_passing_summary(tmp_path):
    outcomes = ca.run([ca.Check("ok", _py("pass"), tmp_path)], echo=False)
    assert ca.summary(outcomes).endswith("All checks passed.")


def test_default_checks_match_contributing():
    checks = ca.default_checks(REPO)
    names = [c.name for c in checks]
    for pkg in (p.parent.name for p in REPO.glob("packages/*/pyproject.toml")):
        for kind in ("ruff check", "ruff format", "mypy", "pytest"):
            assert f"{pkg}: {kind}" in names
    # Every repository tool CONTRIBUTING.md lists is run, and every script exists.
    contributing = (REPO / "CONTRIBUTING.md").read_text(encoding="utf-8")
    listed = set(re.findall(r"python tools/(\w+\.py)", contributing)) - {"check_all.py"}
    run_scripts = {Path(a).name for c in checks for a in c.argv if a.endswith(".py")}
    assert listed <= run_scripts
    assert all((TOOLS / s).is_file() for s in run_scripts)
    assert [c.name for c in checks if c.informational] == ["release readiness"]


def test_quick_and_build_options():
    quick = [c.name for c in ca.default_checks(REPO, quick=True)]
    assert not any(n.endswith(": pytest") or n.startswith("release dry run") for n in quick)
    build = ca.default_checks(REPO, build=True)
    assert any(c.name == "release dry run (--build)" and "--build" in c.argv for c in build)
