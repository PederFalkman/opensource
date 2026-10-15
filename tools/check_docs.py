#!/usr/bin/env python3
"""Keep the documentation consistent with the code.

Checks:

1. Every public name in a package's ``__all__`` (dunders excepted) is
   mentioned in that package's ``README.md``.
2. Every ``QualityFlag`` member appears as ``NAME`` in the README flag table.
3. Every package ``CHANGELOG.md`` has an ``## [Unreleased]`` section.
4. Every relative Markdown link in tracked docs points to an existing file.

Code is read with ``ast`` and never imported, so this needs no dependencies.

Usage: ``python tools/check_docs.py [REPO_ROOT]``
"""

from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_SKIP_DIRS = {".git", "dist", "build", ".venv", "node_modules", ".mypy_cache", ".ruff_cache", ".pytest_cache"}


@dataclass(frozen=True)
class Problem:
    path: Path
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


def _module_ast(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def public_names(init_path: Path) -> list[str]:
    for node in _module_ast(init_path).body:
        is_all = isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets
        )
        if is_all and isinstance(node.value, (ast.List, ast.Tuple)):
            return [
                e.value for e in node.value.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)
            ]
    return []


def enum_members(module_path: Path, class_name: str) -> list[str]:
    for node in ast.walk(_module_ast(module_path)):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return [
                t.id
                for s in node.body
                if isinstance(s, ast.Assign)
                for t in s.targets
                if isinstance(t, ast.Name)
            ]
    return []


def check_package(root: Path, pkg_dir: Path) -> list[Problem]:
    problems: list[Problem] = []
    readme = pkg_dir / "README.md"
    text = readme.read_text(encoding="utf-8") if readme.is_file() else ""
    rel = readme.relative_to(root)
    if not text:
        problems.append(Problem(rel, "missing or empty"))

    for init in sorted((pkg_dir / "src").glob("*/__init__.py")):
        for name in public_names(init):
            if name.startswith("__"):
                continue
            if not re.search(rf"(?<![\w.]){re.escape(name)}(?!\w)", text):
                problems.append(
                    Problem(rel, f"public name {name!r} from {init.relative_to(root)} not mentioned")
                )
        flags = init.parent / "flags.py"
        if flags.is_file():
            for member in enum_members(flags, "QualityFlag"):
                if f"`{member}`" not in text:
                    problems.append(Problem(rel, f"QualityFlag.{member} missing from the flag table"))

    changelog = pkg_dir / "CHANGELOG.md"
    if not changelog.is_file() or "## [Unreleased]" not in changelog.read_text(encoding="utf-8"):
        problems.append(Problem(changelog.relative_to(root), "needs an '## [Unreleased]' section"))
    return problems


def markdown_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.md") if not _SKIP_DIRS & set(p.relative_to(root).parts))


def check_links(root: Path) -> list[Problem]:
    problems = []
    for path in markdown_files(root):
        in_code = False
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if line.lstrip().startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                continue
            for target in _LINK.findall(line):
                if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.IGNORECASE) or target.startswith("#"):
                    continue  # URL, mailto: or in-page anchor
                file_part = target.split("#", 1)[0]
                if file_part and not (path.parent / file_part).exists():
                    problems.append(Problem(path.relative_to(root), f"line {lineno}: broken link {target!r}"))
    return problems


def run(root: Path) -> list[Problem]:
    problems: list[Problem] = []
    for pyproject in sorted(root.glob("packages/*/pyproject.toml")):
        problems.extend(check_package(root, pyproject.parent))
    problems.extend(check_links(root))
    return problems


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parent.parent
    problems = run(root)
    for p in problems:
        print(f"DOCS: {p}", file=sys.stderr)
    if problems:
        print(f"{len(problems)} documentation problem(s).", file=sys.stderr)
        return 1
    print("Documentation checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
