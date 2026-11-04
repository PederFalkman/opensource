#!/usr/bin/env python3
"""Report the release diff without granting publication approval.

Use an explicitly named base tag and head ref. Read-only: no tags, commits,
uploads or release actions. Workbench changes are not Python-package changes.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

PACKAGE_ROOT = "packages/energydata-kit/"
SOURCE_ROOT = PACKAGE_ROOT + "src/energydata_kit/"
VERSION_FILE = SOURCE_ROOT + "__init__.py"
WORKBENCH_ROOT = "apps/workbench/"


def classify(files: list[str]) -> dict[str, object]:
    unique = sorted(set(files))
    python_package = [p for p in unique if p.startswith(PACKAGE_ROOT)]
    source = [p for p in python_package if p.startswith(SOURCE_ROOT)]
    implementation = [p for p in source if p != VERSION_FILE]
    workbench = [p for p in unique if p.startswith(WORKBENCH_ROOT)]
    metadata = [p for p in python_package if p not in source]
    return {
        "total_changed_files": len(unique),
        "python_package_files": python_package,
        "python_source_files": source,
        "python_implementation_files_excluding_version_module": implementation,
        "python_package_metadata_or_docs": metadata,
        "workbench_files": workbench,
        "python_implementation_change_detected": bool(implementation),
        "python_source_review_required": bool(source),
        "workbench_change_detected": bool(workbench),
        "review_notice": (
            "Path-level inventory only: source, compatibility and IP impact "
            "must still be reviewed. Any changed Python source including __init__.py "
            "requires content review; the classifier cannot infer version-only edits."
        ),
    }


def changed_files(root: Path, base: str, head: str) -> list[str]:
    # Separate arguments and no shell prevent ref-based shell injection.
    # --no-renames ensures every record has one status and one path.
    proc = subprocess.run(
        ["git", "-C", str(root), "diff", "--no-renames", "--name-only", "-z", base, head],
        capture_output=True,
        check=True,
    )
    return [part.decode("utf-8") for part in proc.stdout.split(b"\0") if part]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--base", default="energydata-kit-v0.16.0")
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args(argv)
    # Reject option-like refs and unsupported selectors. Never allow a diff
    # across an accidentally omitted or implicit baseline.
    for name, value in (("base", args.base), ("head", args.head)):
        if not value or value.startswith("-") or any(c.isspace() for c in value):
            parser.error(f"{name} must be an explicit git revision")
    try:
        inventory = classify(changed_files(args.root, args.base, args.head))
    except (OSError, subprocess.CalledProcessError, UnicodeDecodeError) as exc:
        print(f"Cannot establish exact release diff: {exc}", file=sys.stderr)
        return 2
    payload = {
        "schema_version": "solid-soup.release-scope.v1",
        "base": args.base,
        "head": args.head,
        "publication_approved": False,
        "scope": inventory,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
