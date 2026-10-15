#!/usr/bin/env python3
"""Automated IP-boundary checks for the packages in this repository.

Checks, per package under ``packages/``:

1. No Python file imports a forbidden (proprietary) top-level module.
2. Every declared dependency (runtime, optional extras, dependency groups) is
   on the reviewed allowlist in ``tools/ip_boundary.toml``.
3. No dependency is a direct or VCS reference (``pkg @ git+...``, URLs),
   which could pull code from private repositories.

These are tripwires, not proof of compliance; see
docs/governance/IP_BOUNDARY.md. Standard library only.

Usage: ``python tools/check_ip_boundary.py [REPO_ROOT]``
"""

from __future__ import annotations

import ast
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

CONFIG_PATH = Path("tools") / "ip_boundary.toml"
_REQ_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


@dataclass(frozen=True)
class Violation:
    path: Path
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _is_forbidden(module: str, forbidden: list[str]) -> bool:
    top = module.split(".", 1)[0].lower()
    return any(top == f or top.startswith(f + "_") for f in forbidden)


def check_imports(path: Path, forbidden: list[str]) -> list[Violation]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        return [Violation(path, f"could not parse: {exc}")]
    found = []
    for node in ast.walk(tree):
        modules: list[str] = []
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules = [node.module]
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, (ast.Name, ast.Attribute))
            and (getattr(node.func, "id", None) or getattr(node.func, "attr", None))
            in {"import_module", "__import__"}
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            modules = [node.args[0].value]
        for module in modules:
            if _is_forbidden(module, forbidden):
                found.append(Violation(path, f"line {node.lineno}: forbidden import {module!r}"))
    return found


def declared_requirements(pyproject: dict[str, object]) -> list[str]:
    project = pyproject.get("project", {})
    assert isinstance(project, dict)
    reqs: list[str] = list(project.get("dependencies", []))
    for extra in project.get("optional-dependencies", {}).values():
        reqs.extend(extra)
    groups = pyproject.get("dependency-groups", {})
    assert isinstance(groups, dict)
    for group in groups.values():
        reqs.extend(r for r in group if isinstance(r, str))  # skip {include-group = ...}
    build = pyproject.get("build-system", {})
    assert isinstance(build, dict)
    reqs.extend(build.get("requires", []))
    return reqs


def check_dependencies(pyproject_path: Path, allowed: list[str]) -> list[Violation]:
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    allowed_norm = {normalize(a) for a in allowed}
    found = []
    for req in declared_requirements(data):
        if "@" in req or "://" in req:
            found.append(Violation(pyproject_path, f"direct/VCS reference not allowed: {req!r}"))
            continue
        match = _REQ_NAME.match(req)
        if not match:
            found.append(Violation(pyproject_path, f"unparseable requirement {req!r}"))
            continue
        name = normalize(match.group(1))
        if name not in allowed_norm:
            found.append(
                Violation(pyproject_path, f"dependency {name!r} is not in the allowlist ({CONFIG_PATH})")
            )
    return found


def run(root: Path) -> list[Violation]:
    config = tomllib.loads((root / CONFIG_PATH).read_text(encoding="utf-8"))
    forbidden = [f.lower() for f in config["forbidden_imports"]]
    allowlists: dict[str, list[str]] = config["allowed_dependencies"]

    violations: list[Violation] = []
    packages = sorted(p.parent for p in (root / "packages").glob("*/pyproject.toml"))
    for pkg in packages:
        pyproject = pkg / "pyproject.toml"
        name = tomllib.loads(pyproject.read_text(encoding="utf-8")).get("project", {}).get("name", "")
        if name not in allowlists:
            violations.append(Violation(pyproject, f"package {name!r} has no allowlist in {CONFIG_PATH}"))
        else:
            violations.extend(check_dependencies(pyproject, allowlists[name]))
        for py in sorted(pkg.rglob("*.py")):
            violations.extend(check_imports(py, forbidden))
    for py in sorted((root / "tools").glob("*.py")):
        violations.extend(check_imports(py, forbidden))
    return violations


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parent.parent
    violations = run(root)
    for v in violations:
        print(f"IP-BOUNDARY: {v}", file=sys.stderr)
    if violations:
        print(f"{len(violations)} IP-boundary violation(s).", file=sys.stderr)
        return 1
    print("IP-boundary checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
