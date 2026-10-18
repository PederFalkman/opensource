#!/usr/bin/env python3
"""Rehearse a package release in a throwaway copy of the repository.

Applies the edits a release PR would make (see
``docs/governance/RELEASE_CHECKLIST.md``) to a temporary copy, never to the
repository itself:

1. ``__version__`` set to the final version (default: the current version
   without its ``.devN`` suffix);
2. the ``## [Unreleased]`` changelog content moved under a dated
   ``## [X.Y.Z] - YYYY-MM-DD`` heading, with a fresh empty ``[Unreleased]``
   (if that dated heading already exists, anything under ``[Unreleased]`` is
   folded into it instead);
3. a ``LICENSE`` file at the root, a copy in the package directory (only
   files there ship in the wheel and sdist) and a ``license`` declaration,
   all **placeholders** (``LicenseRef-Dry-Run-Placeholder``): no licence is
   chosen or granted here, that is gate G2;
4. the ``Private :: Do Not Upload`` classifier removed.

It then runs ``tools/check_release_readiness.py --strict`` with the matching
tag on the copy. With ``--build`` it also builds the sdist and wheel,
runs ``twine check``, checks the wheel metadata (version, placeholder
licence and licence file, no upload guard) and prints the SHA-256 digests. The copy and
everything built in it are deleted afterwards; nothing is uploaded.

A failure means the next release PR would fail too, so fix it before it
matters. Passing proves only the mechanics; gates G1-G7 still need people.

Usage: ``python tools/release_dry_run.py [PACKAGE] [--version X.Y.Z] [--date YYYY-MM-DD] [--build]``
"""

from __future__ import annotations

import argparse
import datetime as dt
import email.parser
import hashlib
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUARD_CLASSIFIER = "Private :: Do Not Upload"
PLACEHOLDER_LICENSE = "LicenseRef-Dry-Run-Placeholder"
PLACEHOLDER_TEXT = (
    "DRY-RUN PLACEHOLDER - THIS IS NOT A LICENCE.\n\n"
    "Written by tools/release_dry_run.py into a temporary copy of the repository.\n"
    "No licence has been chosen or granted (see docs/governance/RELEASE_GATES.md, gate G2).\n"
)
_VERSION_ASSIGN = re.compile(r"""^(__version__\s*=\s*["'])([^"']+)(["'])""", re.MULTILINE)
_IGNORE = shutil.ignore_patterns(
    ".git", "dist", "build", "*.egg-info", "__pycache__", ".venv", "venv", ".mypy_cache", ".ruff_cache",
    ".pytest_cache",
)  # fmt: skip


class DryRunError(Exception):
    pass


def final_version(current: str) -> str:
    match = re.match(r"^(\d+\.\d+\.\d+)", current)
    if not match:
        raise DryRunError(f"cannot derive a final version from {current!r}")
    return match.group(1)


def init_file(pkg_dir: Path) -> Path:
    inits = sorted((pkg_dir / "src").glob("*/__init__.py"))
    if len(inits) != 1:
        raise DryRunError(f"expected one package under {pkg_dir / 'src'}, found {len(inits)}")
    return inits[0]


def current_version(pkg_dir: Path) -> str:
    match = _VERSION_ASSIGN.search(init_file(pkg_dir).read_text(encoding="utf-8"))
    if not match:
        raise DryRunError("no __version__ assignment found")
    return match.group(2)


def apply_release_edits(root: Path, package: str, version: str, date: str) -> None:
    """Make the release-PR edits in ``root``, which must be a throwaway copy."""
    pkg_dir = root / "packages" / package

    init = init_file(pkg_dir)
    init.write_text(_VERSION_ASSIGN.sub(rf"\g<1>{version}\g<3>", init.read_text(encoding="utf-8"), count=1))

    changelog = pkg_dir / "CHANGELOG.md"
    text = changelog.read_text(encoding="utf-8")
    if "## [Unreleased]" not in text:
        raise DryRunError(f"{changelog.name} has no '## [Unreleased]' section")
    dated = re.search(rf"^## \[{re.escape(version)}\] - \d{{4}}-\d{{2}}-\d{{2}}[ \t]*\n", text, re.MULTILINE)
    if dated is None:
        heading = f"## [Unreleased]\n\n## [{version}] - {date}"
        changelog.write_text(text.replace("## [Unreleased]", heading, 1))
    else:
        # The dated section exists already: fold anything added since into it.
        start = text.index("## [Unreleased]")
        body_start = text.index("\n", start) + 1
        pending = text[body_start : dated.start()].strip()
        if pending:
            head, rest = text[:body_start], text[dated.end() :]
            text = f"{head}\n{dated.group(0)}\n{pending}\n{rest}"
            changelog.write_text(text)

    # Only stand in for a licence the repository does not have yet. Once G2 is
    # passed, the real LICENSE and the real `license = ...` are what a release
    # ships, and there is nothing left to rehearse: overwriting them with the
    # placeholder would rehearse the wrong thing, and inserting a second
    # `license` key made the copy invalid TOML ("Cannot overwrite a value")
    # instead of rehearsing anything at all.
    for licence in (root / "LICENSE", pkg_dir / "LICENSE"):
        if not licence.is_file():
            licence.write_text(PLACEHOLDER_TEXT, encoding="utf-8")

    pyproject = pkg_dir / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    already_declared = "license" in tomllib.loads(text).get("project", {})
    lines = text.splitlines(keepends=True)
    out, in_project, declared = [], False, already_declared
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("["):
            in_project = stripped == "[project]"
        if f'"{GUARD_CLASSIFIER}"' in stripped:
            continue
        out.append(line)
        if in_project and not declared and stripped.startswith("requires-python"):
            out.append(f'license = "{PLACEHOLDER_LICENSE}"\n')
            declared = True
    if not declared:
        raise DryRunError("could not place the license declaration (no requires-python in [project])")
    pyproject.write_text("".join(out), encoding="utf-8")


def run(cmd: list[str], cwd: Path) -> str:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise DryRunError(f"{' '.join(cmd)} failed:\n{result.stdout}{result.stderr}")
    return result.stdout


def wheel_metadata(wheel: Path) -> email.message.Message:
    with zipfile.ZipFile(wheel) as zf:
        name = next(n for n in zf.namelist() if n.endswith(".dist-info/METADATA"))
        return email.parser.Parser().parsestr(zf.read(name).decode("utf-8"))


def sdist_has_license(sdist: Path) -> bool:
    with tarfile.open(sdist) as tf:
        return any(name.endswith("/LICENSE") for name in tf.getnames())


def declared_license(pkg_dir: Path) -> str:
    """The licence expression the copy's pyproject declares, placeholder or real."""
    declared = tomllib.loads((pkg_dir / "pyproject.toml").read_text(encoding="utf-8"))["project"]["license"]
    # PEP 639 makes this an SPDX string; a pre-639 table is still accepted here.
    return declared if isinstance(declared, str) else str(declared.get("text", declared))


def check_wheel(wheel: Path, version: str, expected_license: str) -> list[str]:
    meta = wheel_metadata(wheel)
    problems = []
    if meta["Version"] != version:
        problems.append(f"wheel version is {meta['Version']!r}, expected {version!r}")
    if GUARD_CLASSIFIER in (meta.get_all("Classifier") or []):
        problems.append("wheel still carries the upload guard")
    # Compare against what the copy actually declares rather than against the
    # placeholder constant: that holds whether the dry run substituted a
    # placeholder (G2 unmet) or kept the repository's real licence (G2 passed),
    # and it checks the stronger property either way — that the build
    # propagated the declaration into the wheel instead of dropping it.
    if meta.get("License-Expression") != expected_license:
        problems.append(
            f"wheel License-Expression is {meta.get('License-Expression')!r}, "
            f"expected {expected_license!r}"
        )
    if "LICENSE" not in (meta.get_all("License-File") or []):
        problems.append("wheel does not include the LICENSE file")
    return problems


def dry_run(package: str, version: str | None, date: str, build: bool, root: Path = ROOT) -> list[str]:
    """Run the rehearsal; return the report lines. Raises DryRunError on failure."""
    report = []
    with tempfile.TemporaryDirectory(prefix="release-dry-run-") as tmp:
        copy = Path(tmp) / "repo"
        shutil.copytree(root, copy, ignore=_IGNORE)
        pkg_dir = copy / "packages" / package
        if not (pkg_dir / "pyproject.toml").is_file():
            raise DryRunError(f"package {package!r} not found")
        version = version or final_version(current_version(pkg_dir))
        apply_release_edits(copy, package, version, date)
        report.append(f"{package} {version} ({date}): release edits applied to a temporary copy")

        tag = f"{package}-v{version}"
        readiness = [sys.executable, str(copy / "tools" / "check_release_readiness.py")]
        report.append(
            run([*readiness, package, "--strict", "--tag", tag, "--root", str(copy)], copy).rstrip()
        )

        if build:
            dist = Path(tmp) / "dist"
            run([sys.executable, "-m", "build", "--outdir", str(dist), str(pkg_dir)], copy)
            files = sorted(dist.iterdir())
            run([sys.executable, "-m", "twine", "check", "--strict", *map(str, files)], copy)
            wheels = [f for f in files if f.suffix == ".whl"]
            if len(wheels) != 1:
                raise DryRunError(f"expected one wheel, built {len(wheels)}")
            problems = check_wheel(wheels[0], version, declared_license(pkg_dir))
            sdists = [f for f in files if f.name.endswith(".tar.gz")]
            if len(sdists) != 1 or not sdist_has_license(sdists[0]):
                problems.append("sdist does not include the LICENSE file")
            if problems:
                raise DryRunError("; ".join(problems))
            report.append("built and twine-checked (not uploaded; deleted with the copy):")
            report += [f"  {hashlib.sha256(f.read_bytes()).hexdigest()}  {f.name}" for f in files]
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("package", nargs="?", default="energydata-kit")
    parser.add_argument("--version", help="final version to rehearse (default: current without .devN)")
    parser.add_argument("--date", default=dt.datetime.now(dt.UTC).date().isoformat(), help="changelog date")
    parser.add_argument("--build", action="store_true", help="also build, twine-check and inspect the wheel")
    args = parser.parse_args(argv)
    try:
        lines = dry_run(args.package, args.version, args.date, args.build)
    except DryRunError as exc:
        print(f"RELEASE-DRY-RUN: {exc}", file=sys.stderr)
        return 1
    print("\n".join(lines))
    print("Release dry run passed. The repository itself was not changed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
