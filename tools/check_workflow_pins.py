#!/usr/bin/env python3
"""Fail if a GitHub Actions ``uses:`` reference is not pinned immutably.

Rules for every ``uses:`` in ``.github/workflows/*.yml|yaml`` and
``.github/actions/**/action.yml|yaml``:

- ``owner/repo[/path]@<40-hex commit SHA>`` followed by a version comment
  (``# v4.2.2``), which Dependabot keeps in sync with the SHA;
- ``docker://image@sha256:<64-hex digest>``;
- local actions (``./path``) are always allowed.

Tags and branches (``@v4``, ``@main``) are mutable and rejected. Standard
library only.

Usage: ``python tools/check_workflow_pins.py [REPO_ROOT]``
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

_USES = re.compile(r"""^\s*(?:-\s*)?uses:\s*["']?(?P<ref>[^\s"'#]+)["']?\s*(?:#\s*(?P<comment>.*))?$""")
_ACTION = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[^@\s]+)?@(?P<pin>[^\s]+)$")
_SHA = re.compile(r"^[0-9a-f]{40}$")
_DOCKER = re.compile(r"^docker://[^@\s]+@sha256:[0-9a-f]{64}$")
_VERSION_COMMENT = re.compile(r"^v?\d+(\.\d+)*\S*")


@dataclass(frozen=True)
class Violation:
    path: Path
    line: int
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.message}"


def check_text(text: str, path: Path) -> list[Violation]:
    found = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        match = _USES.match(line)
        if not match:
            continue
        ref, comment = match.group("ref"), (match.group("comment") or "").strip()
        if ref.startswith("./"):
            continue
        if ref.startswith("docker://"):
            if not _DOCKER.match(ref):
                found.append(Violation(path, lineno, f"docker image not pinned to a sha256 digest: {ref}"))
            continue
        action = _ACTION.match(ref)
        if not action:
            found.append(Violation(path, lineno, f"unrecognised uses: reference {ref!r}"))
        elif not _SHA.match(action.group("pin")):
            found.append(Violation(path, lineno, f"not pinned to a full commit SHA: {ref}"))
        elif not _VERSION_COMMENT.match(comment):
            hint = "pinned SHA needs a version comment, e.g. '# v4.2.2'"
            found.append(Violation(path, lineno, f"{hint}: {ref}"))
    return found


def workflow_files(root: Path) -> list[Path]:
    github = root / ".github"
    files = [*github.glob("workflows/*.yml"), *github.glob("workflows/*.yaml")]
    files += [*github.glob("actions/**/action.yml"), *github.glob("actions/**/action.yaml")]
    return sorted(files)


def run(root: Path) -> list[Violation]:
    violations: list[Violation] = []
    for path in workflow_files(root):
        violations.extend(check_text(path.read_text(encoding="utf-8"), path.relative_to(root)))
    return violations


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parent.parent
    files = workflow_files(root)
    if not files:
        print(f"WORKFLOW-PINS: no workflow files found under {root}/.github", file=sys.stderr)
        return 1
    violations = run(root)
    for v in violations:
        print(f"WORKFLOW-PINS: {v}", file=sys.stderr)
    if violations:
        print(f"{len(violations)} unpinned action reference(s).", file=sys.stderr)
        return 1
    print(f"All actions pinned to commit SHAs ({len(files)} file(s)).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
