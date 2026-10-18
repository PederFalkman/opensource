import importlib.util
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent.parent
REPO = TOOLS.parent

spec = importlib.util.spec_from_file_location("release_dry_run", TOOLS / "release_dry_run.py")
assert spec and spec.loader
rdr = importlib.util.module_from_spec(spec)
sys.modules["release_dry_run"] = rdr
spec.loader.exec_module(rdr)

PYPROJECT = """[project]
name = "demo"
dynamic = ["version"]
requires-python = ">=3.11"
classifiers = [
    "Typing :: Typed",
    "Private :: Do Not Upload",
]

[tool.hatch.version]
path = "src/demo/__init__.py"
"""


def make_repo(tmp_path: Path, version: str = "0.3.0.dev2") -> Path:
    pkg = tmp_path / "packages" / "demo"
    (pkg / "src" / "demo").mkdir(parents=True)
    (pkg / "src" / "demo" / "__init__.py").write_text(f'"""Demo."""\n\n__version__ = "{version}"\n')
    (pkg / "pyproject.toml").write_text(PYPROJECT)
    (pkg / "CHANGELOG.md").write_text("# Changelog\n\n## [Unreleased]\n\n### Added\n- Things.\n")
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "check_release_readiness.py").write_text(
        (TOOLS / "check_release_readiness.py").read_text()
    )
    return tmp_path


def test_release_edits_keep_an_existing_dated_section(tmp_path):
    root = make_repo(tmp_path, version="0.3.0")
    changelog = root / "packages" / "demo" / "CHANGELOG.md"
    changelog.write_text("# Changelog\n\n## [Unreleased]\n\n## [0.3.0] - 2026-10-01\n\n- Things.\n")
    rdr.apply_release_edits(root, "demo", "0.3.0", "2026-11-01")
    text = changelog.read_text()
    assert text.count("## [0.3.0]") == 1
    assert "2026-11-01" not in text


def test_release_edits_fold_unreleased_into_an_existing_dated_section(tmp_path):
    root = make_repo(tmp_path, version="0.3.0")
    changelog = root / "packages" / "demo" / "CHANGELOG.md"
    changelog.write_text(
        "# Changelog\n\n## [Unreleased]\n\n### Fixed\n- Late fix.\n\n## [0.3.0] - 2026-10-01\n\n- Things.\n"
    )
    rdr.apply_release_edits(root, "demo", "0.3.0", "2026-11-01")
    text = changelog.read_text()
    assert text.index("## [Unreleased]") < text.index("## [0.3.0] - 2026-10-01") < text.index("- Late fix.")
    assert text.index("- Late fix.") < text.index("- Things.")
    assert "\n## [Unreleased]\n\n## [0.3.0]" in text


def test_final_version():
    assert rdr.final_version("0.1.0.dev0") == "0.1.0"
    assert rdr.final_version("1.2.3rc1") == "1.2.3"
    with pytest.raises(rdr.DryRunError):
        rdr.final_version("next")


def test_release_edits(tmp_path):
    root = make_repo(tmp_path)
    rdr.apply_release_edits(root, "demo", "0.3.0", "2026-11-01")
    pkg = root / "packages" / "demo"
    assert '__version__ = "0.3.0"' in (pkg / "src" / "demo" / "__init__.py").read_text()
    changelog = (pkg / "CHANGELOG.md").read_text()
    assert changelog.index("## [Unreleased]") < changelog.index("## [0.3.0] - 2026-11-01")
    assert changelog.index("## [0.3.0] - 2026-11-01") < changelog.index("- Things.")
    pyproject = (pkg / "pyproject.toml").read_text()
    assert 'license = "LicenseRef-Dry-Run-Placeholder"' in pyproject
    assert "Private :: Do Not Upload" not in pyproject and "Typing :: Typed" in pyproject
    for licence in (root / "LICENSE", pkg / "LICENSE"):
        assert licence.read_text().startswith("DRY-RUN PLACEHOLDER - THIS IS NOT A LICENCE.")


def test_release_edits_do_not_double_declare_an_existing_licence(tmp_path):
    """The regression that broke CI on the PR that passed G2.

    The dry run rehearses *adding* a licence. Once the repository has one, the
    old code appended a second ``license`` key and wrote the placeholder over
    the real text, so the throwaway copy was invalid TOML and the whole dry run
    died with "Cannot overwrite a value" instead of rehearsing a release.
    """
    root = make_repo(tmp_path)
    pkg = root / "packages" / "demo"
    pyproject = pkg / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text().replace(
            'requires-python = ">=3.11"', 'requires-python = ">=3.11"\nlicense = "Apache-2.0"', 1
        )
    )
    (root / "LICENSE").write_text("Apache License\nVersion 2.0, January 2004\n")
    (pkg / "LICENSE").write_text("Apache License\nVersion 2.0, January 2004\n")

    rdr.apply_release_edits(root, "demo", "0.3.0", "2026-11-01")

    text = pyproject.read_text()
    assert tomllib.loads(text)["project"]["license"] == "Apache-2.0"
    assert text.count("license =") == 1
    assert rdr.PLACEHOLDER_LICENSE not in text
    # The real licence text survives; the placeholder never overwrites it.
    for licence in (root / "LICENSE", pkg / "LICENSE"):
        assert licence.read_text().startswith("Apache License")
    # The G7 rehearsal still happens — that gate is not passed.
    assert "Private :: Do Not Upload" not in text


def test_dry_run_passes_and_leaves_source_untouched(tmp_path):
    root = make_repo(tmp_path)
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    lines = rdr.dry_run("demo", None, "2026-11-01", build=False, root=root)
    assert lines[0] == "demo 0.3.0 (2026-11-01): release edits applied to a temporary copy"
    assert "Mechanical release checks pass" in lines[1]
    assert {p: p.read_bytes() for p in root.rglob("*") if p.is_file()} == before


def test_dry_run_reports_what_a_release_would_trip_on(tmp_path):
    root = make_repo(tmp_path)
    (root / "packages" / "demo" / "CHANGELOG.md").write_text("# Changelog\n")
    with pytest.raises(rdr.DryRunError, match="no '## \\[Unreleased\\]' section"):
        rdr.dry_run("demo", None, "2026-11-01", build=False, root=root)
    with pytest.raises(rdr.DryRunError, match="not found"):
        rdr.dry_run("absent", None, "2026-11-01", build=False, root=root)


def test_real_repository_dry_run_without_build():
    before = subprocess.run(["git", "status", "--porcelain"], cwd=REPO, capture_output=True, text=True).stdout
    assert rdr.main(["energydata-kit", "--date", "2026-11-01"]) == 0
    after = subprocess.run(["git", "status", "--porcelain"], cwd=REPO, capture_output=True, text=True).stdout
    assert after == before
