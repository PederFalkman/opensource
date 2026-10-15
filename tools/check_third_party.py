#!/usr/bin/env python3
"""Keep the third-party licence table in sync with the declared dependencies.

Checks, per package under ``packages/``, against the "Direct dependencies of
`<package>`" table in ``docs/governance/THIRD_PARTY_LICENSES.md``:

1. Every declared dependency has exactly one row, and no row is left over.
2. Each row's scopes match where the dependency is declared: ``runtime``,
   ``extra:<name>``, ``dev`` (or another dependency group name) and
   ``build``.
3. Every row names a licence.
4. Dependencies shipped to users (``runtime`` and extras) have no copyleft
   licence unless a permissive alternative is offered (``... OR ...``).

``--report`` instead lists the installed runtime dependencies, direct and
indirect, with the licence each declares in its metadata, as Markdown rows
to compare with the tables. Run it in an environment where the
package is installed. Standard library only.

Usage: ``python tools/check_third_party.py [REPO_ROOT]``
       ``python tools/check_third_party.py --report [PACKAGE]``
"""

from __future__ import annotations

import importlib.metadata as md
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

DOC_PATH = Path("docs") / "governance" / "THIRD_PARTY_LICENSES.md"
_REQ_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
_ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|([^|]*)\|([^|]*)\|")
_COPYLEFT = re.compile(r"\b(A?GPL|LGPL|MPL|EPL|EUPL|SSPL|CDDL)", re.IGNORECASE)


@dataclass(frozen=True)
class Problem:
    path: Path
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _name(requirement: str) -> str | None:
    match = _REQ_NAME.match(requirement)
    return normalize(match.group(1)) if match else None


def declared_scopes(pyproject: dict[str, object]) -> dict[str, set[str]]:
    """Map each declared dependency to the scopes it is declared in."""
    scopes: dict[str, set[str]] = {}

    def add(requirements: object, scope: str) -> None:
        assert isinstance(requirements, list)
        for req in requirements:
            if isinstance(req, str) and (name := _name(req)):  # skip {include-group = ...}
                scopes.setdefault(name, set()).add(scope)

    project = pyproject.get("project", {})
    assert isinstance(project, dict)
    add(project.get("dependencies", []), "runtime")
    for extra, reqs in project.get("optional-dependencies", {}).items():
        add(reqs, f"extra:{extra}")
    groups = pyproject.get("dependency-groups", {})
    assert isinstance(groups, dict)
    for group, reqs in groups.items():
        add(reqs, group)
    build = pyproject.get("build-system", {})
    assert isinstance(build, dict)
    add(build.get("requires", []), "build")
    return scopes


def table_rows(doc: str, package: str) -> dict[str, tuple[set[str], str]] | None:
    """Rows of the package's direct-dependency table: name -> (scopes, licence)."""
    heading = f"## Direct dependencies of `{package}`"
    if heading not in doc:
        return None
    section = doc.split(heading, 1)[1].split("\n## ", 1)[0]
    rows: dict[str, tuple[set[str], str]] = {}
    for line in section.splitlines():
        match = _ROW.match(line)
        if match:
            scopes = {s.strip() for s in match.group(2).split(",") if s.strip()}
            rows[normalize(match.group(1))] = (scopes, match.group(3).strip())
    return rows


def check_package(pyproject_path: Path, doc: str) -> list[Problem]:
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    package = str(data.get("project", {}).get("name", ""))
    rows = table_rows(doc, package)
    if rows is None:
        return [Problem(DOC_PATH, f"no 'Direct dependencies of `{package}`' table")]
    problems = []
    declared = declared_scopes(data)
    for name, scopes in sorted(declared.items()):
        if name not in rows:
            problems.append(Problem(DOC_PATH, f"{package}: dependency {name!r} has no row"))
        elif rows[name][0] != scopes:
            problems.append(
                Problem(
                    DOC_PATH,
                    f"{package}: {name!r} scopes are {sorted(rows[name][0])}, declared as {sorted(scopes)}",
                )
            )
    for name, (scopes, licence) in sorted(rows.items()):
        if name not in declared:
            problems.append(Problem(DOC_PATH, f"{package}: row {name!r} is not a declared dependency"))
        if not licence:
            problems.append(Problem(DOC_PATH, f"{package}: {name!r} has no licence"))
        shipped = any(s == "runtime" or s.startswith("extra:") for s in scopes)
        if shipped and _COPYLEFT.search(licence) and " OR " not in licence:
            problems.append(
                Problem(DOC_PATH, f"{package}: shipped dependency {name!r} is copyleft ({licence})")
            )
    return problems


def run(root: Path) -> list[Problem]:
    doc_file = root / DOC_PATH
    if not doc_file.is_file():
        return [Problem(DOC_PATH, "missing")]
    doc = doc_file.read_text(encoding="utf-8")
    problems: list[Problem] = []
    for pyproject in sorted(root.glob("packages/*/pyproject.toml")):
        problems.extend(check_package(pyproject, doc))
    return problems


def declared_licence(dist: md.Distribution) -> str:
    meta = dist.metadata
    if meta.get("License-Expression"):
        return str(meta["License-Expression"])
    classifiers = [
        c.split(" :: ")[-1] for c in meta.get_all("Classifier") or [] if c.startswith("License ::")
    ]
    if classifiers:
        return " / ".join(classifiers)
    text = (meta.get("License") or "").strip()
    return text.splitlines()[0][:60] if text else "UNKNOWN"


def report(package: str) -> list[str]:
    """Markdown rows for the installed, non-optional dependencies of ``package``, direct and indirect."""
    direct = {n for r in md.requires(package) or [] if "extra ==" not in r and (n := _name(r))}
    seen: dict[str, tuple[str, str]] = {}
    queue = [(name, package) for name in sorted(direct)]
    while queue:
        name, parent = queue.pop(0)
        try:
            dist = md.distribution(name)
        except md.PackageNotFoundError:
            continue  # e.g. a platform-specific requirement not installed here
        key = normalize(dist.metadata["Name"])
        if key in seen:
            continue
        seen[key] = (parent, f"{dist.version}")
        for req in dist.requires or []:
            child = _name(req)
            if child and "extra ==" not in req:
                queue.append((child, key))
    return [
        f"| `{name}` | {parent} | {declared_licence(md.distribution(name))} | {version} |"
        for name, (parent, version) in sorted(seen.items())
    ]


def main(argv: list[str]) -> int:
    if len(argv) > 1 and argv[1] == "--report":
        package = argv[2] if len(argv) > 2 else "energydata-kit"
        try:
            rows = report(package)
        except md.PackageNotFoundError:
            print(f"{package} is not installed in this environment", file=sys.stderr)
            return 2
        print("| Package | Required by | Declared licence | Installed version |")
        print("|---|---|---|---|")
        print("\n".join(rows))
        return 0
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parent.parent
    problems = run(root)
    for p in problems:
        print(f"THIRD-PARTY: {p}", file=sys.stderr)
    if problems:
        print(f"{len(problems)} third-party licence problem(s).", file=sys.stderr)
        return 1
    print("Third-party licence table matches the declared dependencies.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
