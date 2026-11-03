"""WEB-08: generate a local, inspectable manifest of candidate static assets.

This utility does NOT approve, publish, sign or upload an asset. It only
records hashes, lengths and relative file names for a chosen local directory.

Example:
    python apps/workbench/build_asset_manifest.py \
      --assets-dir /tmp/edk-reviewed-assets \
      --output /tmp/edk-asset-manifest.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

MAX_FILES = 1000
MAX_TOTAL_BYTES = 512 * 1024 * 1024
CHUNK = 1024 * 1024


class ManifestError(ValueError):
    """A local candidate asset bundle is unsafe or incomplete."""


def build_manifest(root: Path) -> dict[str, object]:
    """Enumerate regular files without dereferencing symlinks or network URLs."""
    if not root.is_dir() or root.is_symlink():
        raise ManifestError("Assets directory must be a real local directory")
    manifest_files: list[dict[str, object]] = []
    total = 0
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ManifestError("Symlinks are not allowed in candidate asset bundles")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ManifestError("Only regular files are accepted")
        if len(manifest_files) >= MAX_FILES:
            raise ManifestError("Too many files in candidate bundle")
        relative = path.relative_to(root).as_posix()
        if not relative or relative.startswith("/") or ".." in Path(relative).parts:
            raise ManifestError("Invalid asset path")
        size = path.stat().st_size
        total += size
        if total > MAX_TOTAL_BYTES:
            raise ManifestError("Candidate bundle exceeds 512 MiB limit")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            while block := stream.read(CHUNK):
                digest.update(block)
        manifest_files.append({
            "path": relative,
            "bytes": size,
            "sha256": digest.hexdigest(),
        })
    if not manifest_files:
        raise ManifestError("Candidate bundle contains no files")
    return {
        "schema_version": "1",
        "status": "candidate-not-approved",
        "purpose": "review-only-static-asset-inventory",
        "total_bytes": total,
        "assets": manifest_files,
    }


def main(argv: list[str] | None = None) -> int:
    """Print or save a deterministic manifest without deployment side effects."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets-dir", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        report = build_manifest(args.assets_dir)
        payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.output:
            target = args.output.resolve()
            base = args.assets_dir.resolve()
            if target == base or base in target.parents:
                raise ManifestError("Output must be outside the asset directory")
            args.output.write_text(payload, encoding="utf-8")
        else:
            print(payload, end="")
        return 0
    except (ManifestError, OSError) as exc:
        print(f"Manifest generation failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
