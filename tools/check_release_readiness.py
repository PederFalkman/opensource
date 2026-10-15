#!/usr/bin/env python3
"""Report whether a package meets the mechanical release conditions.

These are the parts of docs/governance/RELEASE_GATES.md a script can see.
Passing them is necessary, not sufficient: gates G1-G7 still need people.

Checks, per package under ``packages/``:

- the version is a final release (``X.Y.Z``, no ``dev``/``a``/``b``/``rc``);
- ``CHANGELOG.md`` has a dated section ``## [X.Y.Z] - YYYY-MM-DD``;
- a ``LICENSE`` file exists at the repository root (gate G2);
- ``pyproject.toml`` declares a ``license`` (gate G2);
- the ``Private :: Do Not Upload`` classifier is gone (gate G7);
- with ``--tag``, the tag equals ``<package>-v<version>``.

By default it prints the status and exits 0; ``--strict`` exits 1 if any
check fails. Standard library only.

Usage: ``python tools/check_release_readiness.py [PACKAGE] [--strict] [--tag TAG] [--root DIR]``
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

GUARD_CLASSIFIER = "Private :: Do Not Upload"
_FINAL_VERSION = re.compile(r"^\d+\.\d+\.\d+$")
_VERSION_ASSIGN = re.compile(r"""^__version__\s*=\s*["']([^"']+)["']""", re.MULTILINE)


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str


def _version(pkg_dir: Path, pyproject: dict[str, object]) -> str | None:
    project = pyproject.get("project", {})
    assert isinstance(project, dict)
    if "version" in project:
        return str(project["version"])
    hatch = pyproject.get("tool", {})
    assert isinstance(hatch, dict)
    path = hatch.get("hatch", {}).get("version", {}).get("path")
    if path:
        match = _VERSION_ASSIGN.search((pkg_dir / path).read_text(encoding="utf-8"))
        return match.group(1) if match else None
    return None


def check_package(root: Path, name: str, tag: str | None = None) -> list[Check]:
    pkg_dir = root / "packages" / name
    pyproject_path = pkg_dir / "pyproject.toml"
    if not pyproject_path.is_file():
        return [Check("package exists", False, f"{pyproject_path.relative_to(root)} not found")]
    pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project = pyproject.get("project", {})
    version = _version(pkg_dir, pyproject)

    checks = [
        Check(
            "final version",
            bool(version and _FINAL_VERSION.match(version)),
            f"version is {version!r}" + ("" if version else " (not found)"),
        )
    ]

    changelog = pkg_dir / "CHANGELOG.md"
    heading = None
    if version and changelog.is_file():
        pattern = rf"^## \[{re.escape(version)}\] - \d{{4}}-\d{{2}}-\d{{2}}\s*$"
        heading = re.search(pattern, changelog.read_text(encoding="utf-8"), re.MULTILINE)
    checks.append(
        Check(
            "dated changelog section",
            heading is not None,
            f"found {heading.group(0).strip()!r}" if heading else f"no '## [{version}] - YYYY-MM-DD' heading",
        )
    )

    has_license_file = any((root / n).is_file() for n in ("LICENSE", "LICENSE.txt", "LICENSE.md"))
    checks.append(
        Check("LICENSE file", has_license_file, "present" if has_license_file else "missing (gate G2)")
    )

    declared = project.get("license") if isinstance(project, dict) else None
    checks.append(
        Check(
            "license declared",
            bool(declared),
            f"license = {declared!r}" if declared else "no license in pyproject.toml (gate G2)",
        )
    )

    classifiers = project.get("classifiers", []) if isinstance(project, dict) else []
    guarded = GUARD_CLASSIFIER in classifiers
    checks.append(
        Check(
            "upload guard removed",
            not guarded,
            f"'{GUARD_CLASSIFIER}' still present (gate G7)" if guarded else "removed",
        )
    )

    if tag is not None:
        expected = f"{name}-v{version}"
        checks.append(Check("tag matches version", tag == expected, f"tag {tag!r}, expected {expected!r}"))
    return checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("package", nargs="?", help="package directory name under packages/ (default: all)")
    parser.add_argument("--strict", action="store_true", help="exit 1 if any check fails")
    parser.add_argument("--tag", help="release tag to compare with the version")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args(argv)

    names = (
        [args.package]
        if args.package
        else sorted(p.parent.name for p in args.root.glob("packages/*/pyproject.toml"))
    )
    if not names:
        print("RELEASE-READINESS: no packages found", file=sys.stderr)
        return 1
    failed = False
    for name in names:
        print(f"{name}:")
        for check in check_package(args.root, name, args.tag):
            failed |= not check.ok
            print(f"  [{'PASS' if check.ok else 'FAIL'}] {check.name}: {check.detail}")
    if failed:
        print("Not ready for release (see docs/governance/RELEASE_GATES.md).")
        return 1 if args.strict else 0
    print("Mechanical release checks pass; human gates G1-G7 still apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
