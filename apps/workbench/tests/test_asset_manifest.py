"""Offline regression tests for the WEB-08 candidate static-asset manifest."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("web08_manifest", HERE / "build_asset_manifest.py")
assert SPEC and SPEC.loader
manifest = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manifest)


def test_manifest_deterministic_and_reviews_only(tmp_path: Path) -> None:
    assets = tmp_path / "assets"
    (assets / "runtime").mkdir(parents=True)
    (assets / "runtime" / "example.whl").write_bytes(b"trusted-source-build-example")
    (assets / "pyodide.js").write_text("synthetic, no deployment", encoding="utf-8")
    result = manifest.build_manifest(assets)
    assert result["status"] == "candidate-not-approved"
    assert result["schema_version"] == "1"
    assert result["total_bytes"] == sum(
        item["bytes"] for item in result["assets"]
    )
    assert [item["path"] for item in result["assets"]] == [
        "pyodide.js", "runtime/example.whl"
    ]
    assert result == manifest.build_manifest(assets)
    assert result["assets"][1]["sha256"] == hashlib.sha256(
        b"trusted-source-build-example"
    ).hexdigest()


def test_manifest_refuses_empty_bundle(tmp_path: Path) -> None:
    with pytest.raises(manifest.ManifestError, match="no files"):
        manifest.build_manifest(tmp_path)


def test_manifest_refuses_symlink(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "asset.whl").write_bytes(b"good")
    (root / "hidden.whl").symlink_to(root / "asset.whl")
    with pytest.raises(manifest.ManifestError, match="Symlinks"):
        manifest.build_manifest(root)


def test_manifest_never_writes_inside_asset_directory(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    root.mkdir()
    (root / "file.txt").write_text("local")
    assert manifest.main([
        "--assets-dir", str(root),
        "--output", str(root / "manifest.json"),
    ]) == 2
    assert not (root / "manifest.json").exists()


def test_manifest_is_only_metadata(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    root.mkdir()
    (root / "file.txt").write_text("not a real binary")
    report = manifest.build_manifest(root)
    assert "download_url" not in str(report)
    assert "approved" not in report or report["status"] != "approved"
