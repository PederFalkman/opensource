#!/usr/bin/env python3
"""Report whether a package meets the mechanical release conditions.

These are the parts of docs/governance/RELEASE_GATES.md a script can see.
Passing them is necessary, not sufficient: gates G1-G7 still need people.

Checks, per package under ``packages/``:

- the version is a final release (``X.Y.Z``, no ``dev``/``a``/``b``/``rc``);
- ``CHANGELOG.md`` has a dated section ``## [X.Y.Z] - YYYY-MM-DD``;
- with a final version, ``## [Unreleased]`` is empty: anything listed there
  would ship in ``X.Y.Z`` without being named in its section;
- a ``LICENSE`` file exists at the repository root (gate G2);
- the package directory has its own copy of it, identical to the root one,
  because the build backend only ships licence files from inside the
  package directory (in the wheel and sdist);
- ``pyproject.toml`` declares a ``license`` (gate G2);
- the ``Private :: Do Not Upload`` classifier is gone (gate G7);
- ``docs/governance/RELEASE_DECISIONS.md`` records publication as approved
  (decision D6) on a line ``**D6 approved:** YYYY-MM-DD ...``;
- with ``--tag``, the tag equals ``<package>-v<version>``.

By default it prints the status and exits 0; ``--strict`` exits 1 if any
check fails. ``--guard`` checks one thing only, and is meant to run on every
change: the upload guard may be removed only once D6 is recorded as approved,
so a premature release merge cannot pass CI by editing the guard and its test
together (OSS-83). Standard library only.

Usage: ``python tools/check_release_readiness.py [PACKAGE] [--strict | --guard] [--tag TAG] [--root DIR]``
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

GUARD_CLASSIFIER = "Private :: Do Not Upload"
LICENSE_NAMES = ("LICENSE", "LICENSE.txt", "LICENSE.md")
_FINAL_VERSION = re.compile(r"^\d+\.\d+\.\d+$")
_VERSION_ASSIGN = re.compile(r"""^__version__\s*=\s*["']([^"']+)["']""", re.MULTILINE)
DECISIONS = Path("docs/governance/RELEASE_DECISIONS.md")
_D6_APPROVED = re.compile(r"^\*\*D6 approved:\*\* (\d{4}-\d{2}-\d{2})\b.*$", re.MULTILINE)
_UNRELEASED = re.compile(r"^## \[Unreleased\][^\n]*\n(.*?)(?=^## \[|\Z)", re.MULTILINE | re.DOTALL)


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


def publication_approved(root: Path) -> Check:
    """Whether the decision record has the owner's D6 approval line."""
    path = root / DECISIONS
    match = _D6_APPROVED.search(path.read_text(encoding="utf-8")) if path.is_file() else None
    if match:
        return Check("publication approved (D6)", True, f"recorded: {match.group(0).strip()!r}")
    return Check(
        "publication approved (D6)", False, f"no '**D6 approved:** YYYY-MM-DD' line in {DECISIONS} (gate G7)"
    )


def guarded(pkg_dir: Path) -> bool:
    pyproject = tomllib.loads((pkg_dir / "pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject.get("project", {})
    classifiers = project.get("classifiers", []) if isinstance(project, dict) else []
    return GUARD_CLASSIFIER in classifiers


def check_guard(root: Path, name: str) -> Check:
    """The upload guard is in place, or publication is recorded as approved."""
    if guarded(root / "packages" / name):
        return Check("upload guard kept until D6", True, f"'{GUARD_CLASSIFIER}' present")
    approval = publication_approved(root)
    if approval.ok:
        return Check("upload guard kept until D6", True, f"removed; {approval.detail}")
    return Check(
        "upload guard kept until D6",
        False,
        f"'{GUARD_CLASSIFIER}' was removed but {approval.detail}; restore it, "
        "or record the approval in the same pull request",
    )


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

    unreleased = None
    if changelog.is_file():
        match = _UNRELEASED.search(changelog.read_text(encoding="utf-8"))
        unreleased = match.group(1).strip() if match else None
    if not (version and _FINAL_VERSION.match(version)):
        empty, detail = True, "not checked for a pre-release version"
    elif unreleased:
        empty, detail = False, f"move the '## [Unreleased]' entries into the {version} section"
    else:
        empty, detail = True, "empty"
    checks.append(Check("nothing left unreleased", empty, detail))

    has_license_file = any((root / n).is_file() for n in LICENSE_NAMES)
    checks.append(
        Check("LICENSE file", has_license_file, "present" if has_license_file else "missing (gate G2)")
    )

    root_license = next((root / n for n in LICENSE_NAMES if (root / n).is_file()), None)
    pkg_license = next((pkg_dir / n for n in LICENSE_NAMES if (pkg_dir / n).is_file()), None)
    if pkg_license is None:
        shipped, detail = False, f"no LICENSE in packages/{name}/, so none would ship in the wheel or sdist"
    elif root_license is not None and pkg_license.read_bytes() != root_license.read_bytes():
        shipped, detail = (
            False,
            f"packages/{name}/{pkg_license.name} differs from the root {root_license.name}",
        )
    else:
        shipped, detail = True, f"packages/{name}/{pkg_license.name}"
    checks.append(Check("LICENSE shipped with package", shipped, detail))

    declared = project.get("license") if isinstance(project, dict) else None
    checks.append(
        Check(
            "license declared",
            bool(declared),
            f"license = {declared!r}" if declared else "no license in pyproject.toml (gate G2)",
        )
    )

    has_guard = guarded(pkg_dir)
    checks.append(
        Check(
            "upload guard removed",
            not has_guard,
            f"'{GUARD_CLASSIFIER}' still present (gate G7)" if has_guard else "removed",
        )
    )
    checks.append(publication_approved(root))

    if tag is not None:
        expected = f"{name}-v{version}"
        checks.append(Check("tag matches version", tag == expected, f"tag {tag!r}, expected {expected!r}"))
    return checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("package", nargs="?", help="package directory name under packages/ (default: all)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--strict", action="store_true", help="exit 1 if any check fails")
    mode.add_argument(
        "--guard",
        action="store_true",
        help="only check that the upload guard stays until D6 is recorded as approved; exit 1 if not",
    )
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
    if args.guard:
        results = [(name, check_guard(args.root, name)) for name in names]
        for name, check in results:
            print(f"{name}: [{'PASS' if check.ok else 'FAIL'}] {check.name}: {check.detail}")
        return 0 if all(check.ok for _, check in results) else 1
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
