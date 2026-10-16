#!/usr/bin/env python3
"""Run every local check a contributor should run, and print one summary.

The same commands as in CONTRIBUTING.md, in one go:

- per package under ``packages/``: ``ruff check``, ``ruff format --check``,
  ``mypy`` and ``pytest``;
- repository checks: IP boundary, workflow pins, documentation, third-party
  licences, the tools' own tests and the release dry run;
- the release readiness report, shown for information only (it fails until
  the release gates pass).

Every check runs, even after a failure, so one run shows everything that
needs fixing. The output of failed checks is printed after the summary.
Exit status 1 if any check failed. Standard library only; the package's dev
dependencies (ruff, mypy, pytest) must be installed in the current Python.

Usage: ``python tools/check_all.py [--build] [--quick]``
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable


@dataclass(frozen=True)
class Check:
    name: str
    argv: list[str]
    cwd: Path
    informational: bool = False


@dataclass(frozen=True)
class Outcome:
    check: Check
    returncode: int
    output: str
    seconds: float

    @property
    def status(self) -> str:
        if self.returncode == 0:
            return "PASS"
        return "INFO" if self.check.informational else "FAIL"


def default_checks(root: Path = ROOT, *, build: bool = False, quick: bool = False) -> list[Check]:
    """The checks from CONTRIBUTING.md; ``quick`` skips the slow test suites and the dry run."""
    checks: list[Check] = []
    for pkg in sorted(p.parent for p in root.glob("packages/*/pyproject.toml")):
        name = pkg.name
        checks += [
            Check(f"{name}: ruff check", [PY, "-m", "ruff", "check", "."], pkg),
            Check(f"{name}: ruff format", [PY, "-m", "ruff", "format", "--check", "."], pkg),
            Check(f"{name}: mypy", [PY, "-m", "mypy"], pkg),
        ]
        if not quick:
            checks.append(Check(f"{name}: pytest", [PY, "-m", "pytest", "-q", "-p", "no:cacheprovider"], pkg))
    tools = root / "tools"
    checks += [
        Check("IP boundary", [PY, str(tools / "check_ip_boundary.py")], root),
        Check("workflow pins", [PY, str(tools / "check_workflow_pins.py")], root),
        Check("docs", [PY, str(tools / "check_docs.py")], root),
        Check("third-party licences", [PY, str(tools / "check_third_party.py")], root),
        Check("tools tests", [PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tools/tests"], root),
    ]
    if not quick:
        dry_run = [PY, str(tools / "release_dry_run.py")] + (["--build"] if build else [])
        checks.append(Check("release dry run" + (" (--build)" if build else ""), dry_run, root))
    checks.append(
        Check(
            "release readiness",
            [PY, str(tools / "check_release_readiness.py"), "--strict"],
            root,
            informational=True,
        )
    )
    return checks


def run(checks: list[Check], *, echo: bool = True) -> list[Outcome]:
    outcomes = []
    for check in checks:
        if echo:
            print(f"... {check.name}", flush=True)
        start = time.monotonic()
        result = subprocess.run(check.argv, cwd=check.cwd, capture_output=True, text=True, check=False)
        outcomes.append(
            Outcome(check, result.returncode, result.stdout + result.stderr, time.monotonic() - start)
        )
    return outcomes


def summary(outcomes: list[Outcome]) -> str:
    width = max((len(o.check.name) for o in outcomes), default=0)
    lines = [f"  [{o.status}] {o.check.name:<{width}}  {o.seconds:5.1f}s" for o in outcomes]
    failed = [o for o in outcomes if o.status == "FAIL"]
    for o in failed:
        tail = "\n".join(o.output.rstrip().splitlines()[-30:])
        lines += ["", f"--- {o.check.name} (exit {o.returncode}) ---", tail]
    lines.append("")
    if failed:
        lines.append(f"{len(failed)} of {len(outcomes)} checks failed.")
    else:
        lines.append(
            "All checks passed"
            + (" (release readiness is informational)." if any(o.status == "INFO" for o in outcomes) else ".")
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--build", action="store_true", help="also build the sdist and wheel in the dry run")
    parser.add_argument("--quick", action="store_true", help="skip the package tests and the release dry run")
    args = parser.parse_args(argv)
    outcomes = run(default_checks(build=args.build, quick=args.quick))
    print(summary(outcomes))
    return 1 if any(o.status == "FAIL" for o in outcomes) else 0


if __name__ == "__main__":
    sys.exit(main())
