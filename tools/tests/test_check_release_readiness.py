import importlib.util
import sys
import textwrap
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent.parent
REPO = TOOLS.parent

spec = importlib.util.spec_from_file_location("check_release_readiness", TOOLS / "check_release_readiness.py")
assert spec and spec.loader
crr = importlib.util.module_from_spec(spec)
sys.modules["check_release_readiness"] = crr
spec.loader.exec_module(crr)


def make_repo(
    tmp_path: Path,
    *,
    version: str = "0.1.0",
    changelog: str = "## [0.1.0] - 2026-11-01\n",
    license_file: bool = True,
    package_license: str | None = "license text\n",
    license_field: bool = True,
    guard: bool = False,
    approved: bool = True,
) -> Path:
    pkg = tmp_path / "packages" / "demo"
    (pkg / "src" / "demo").mkdir(parents=True)
    (pkg / "src" / "demo" / "__init__.py").write_text(f'__version__ = "{version}"\n')
    classifiers = '["Private :: Do Not Upload"]' if guard else '["Typing :: Typed"]'
    license_line = 'license = "Apache-2.0"' if license_field else ""
    (pkg / "pyproject.toml").write_text(
        textwrap.dedent(f"""
        [project]
        name = "demo"
        dynamic = ["version"]
        {license_line}
        classifiers = {classifiers}
        [tool.hatch.version]
        path = "src/demo/__init__.py"
        """)
    )
    (pkg / "CHANGELOG.md").write_text("# Changelog\n\n## [Unreleased]\n\n" + changelog)
    if license_file:
        (tmp_path / "LICENSE").write_text("license text\n")
    if package_license is not None:
        (pkg / "LICENSE").write_text(package_license)
    decisions = tmp_path / "docs" / "governance" / "RELEASE_DECISIONS.md"
    decisions.parent.mkdir(parents=True)
    approval = f"**D6 approved:** 2026-11-01, demo {version} on PyPI, by the owner\n" if approved else ""
    decisions.write_text(f"# Release decisions\n\n### D6. Publication\n\n{approval}")
    return tmp_path


def failing(root: Path, tag: str | None = None) -> list[str]:
    return [c.name for c in crr.check_package(root, "demo", tag) if not c.ok]


def test_ready_package_passes(tmp_path):
    root = make_repo(tmp_path)
    assert failing(root) == []
    assert failing(root, tag="demo-v0.1.0") == []
    assert crr.main(["demo", "--strict", "--root", str(root)]) == 0


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"version": "0.1.0.dev0"}, ["final version", "dated changelog section"]),
        ({"version": "0.1.0rc1", "changelog": "## [0.1.0rc1] - 2026-11-01\n"}, ["final version"]),
        ({"changelog": "## [0.1.0] - unreleased\n"}, ["dated changelog section"]),
        ({"license_file": False}, ["LICENSE file"]),
        ({"package_license": None}, ["LICENSE shipped with package"]),
        ({"package_license": "other text\n"}, ["LICENSE shipped with package"]),
        ({"license_field": False}, ["license declared"]),
        ({"guard": True}, ["upload guard removed"]),
        ({"approved": False}, ["publication approved (D6)"]),
    ],
)
def test_each_condition(tmp_path, kwargs, expected):
    assert failing(make_repo(tmp_path, **kwargs)) == expected


def test_tag_must_match(tmp_path):
    assert failing(make_repo(tmp_path), tag="demo-v0.2.0") == ["tag matches version"]


def test_strict_and_report_modes(tmp_path, capsys):
    root = make_repo(tmp_path, guard=True)
    assert crr.main(["demo", "--root", str(root)]) == 0
    assert crr.main(["demo", "--strict", "--root", str(root)]) == 1
    assert "[FAIL] upload guard removed" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("guard", "approved", "ok"),
    [(True, False, True), (True, True, True), (False, True, True), (False, False, False)],
)
def test_guard_mode(tmp_path, capsys, guard, approved, ok):
    # #82 removed the guard and inverted its test together, so CI stayed green (OSS-83).
    root = make_repo(tmp_path, guard=guard, approved=approved)
    assert crr.check_guard(root, "demo").ok is ok
    assert crr.main(["demo", "--guard", "--root", str(root)]) == (0 if ok else 1)
    if not ok:
        assert "record the approval in the same pull request" in capsys.readouterr().out


def test_approval_line_must_be_its_own_dated_line(tmp_path):
    root = make_repo(tmp_path, guard=False, approved=False)
    decisions = root / crr.DECISIONS
    for text in ["Once **D6 approved:** 2026-11-01 is added", "**D6 approved:** soon", "**D6 approved:**"]:
        decisions.write_text(text + "\n")
        assert not crr.check_guard(root, "demo").ok, text
    decisions.write_text("intro\n**D6 approved:** 2026-11-01 demo 0.1.0 (PyPI)\n")
    assert crr.check_guard(root, "demo").ok


@pytest.mark.parametrize(
    "line",
    [
        "**D6 approved:** 2026-11-01, demo 0.0.9 as a GitHub release",  # an earlier release
        "**D6 approved:** 2026-11-01 demo 0.1.0rc1",
        "**D6 approved:** 2026-11-01 demo 10.1.0",
        "**D6 approved:** 2026-11-01 other 0.1.0",
        "**D6 approved:** 2026-11-01 PyPI",  # no package or version
    ],
)
def test_approval_must_name_this_version(tmp_path, line):
    # An approval for one release must not unlock the guard for the next (OSS-98).
    root = make_repo(tmp_path, guard=False, approved=False)
    (root / crr.DECISIONS).write_text(f"**D6 approved:** 2026-10-19 demo 0.0.9\n{line}\n")
    assert not crr.check_guard(root, "demo").ok, line
    assert "publication approved (D6)" in failing(root)


def test_a_dev_version_cannot_drop_the_guard(tmp_path):
    root = make_repo(tmp_path, version="0.2.0.dev0", guard=False, approved=False)
    (root / crr.DECISIONS).write_text("**D6 approved:** 2026-10-19 demo 0.1.0\n")
    assert not crr.check_guard(root, "demo").ok


def test_unreleased_entries_block_a_final_version(tmp_path):
    root = make_repo(tmp_path, changelog="### Fixed\n- Late fix.\n\n## [0.1.0] - 2026-11-01\n")
    assert failing(root) == ["nothing left unreleased"]
    dev = make_repo(tmp_path / "dev", version="0.2.0.dev0", changelog="### Fixed\n- Late fix.\n")
    assert "nothing left unreleased" not in failing(dev)


def test_missing_package(tmp_path):
    assert failing(make_repo(tmp_path)) == []
    assert [c.name for c in crr.check_package(tmp_path, "absent")] == ["package exists"]


def test_real_repository_is_release_ready():
    # Release 0.8.0 (OSS-170): G1, G3, G4 and D6 are recorded, the upload guard
    # is removed (gate G7) and the changelog dated, so every mechanical check
    # passes and --strict exits 0. The next development cycle restores the guard.
    failed = {c.name for c in crr.check_package(REPO, "energydata-kit") if not c.ok}
    assert failed == set(), f"not release-ready: {sorted(failed)}"
    # The licence checks must keep passing: if a LICENSE or the declaration is
    # ever dropped, this fails instead of widening what may be broken.
    licensed = {"LICENSE file", "LICENSE shipped with package", "license declared"}
    assert not (licensed & failed), f"G2 regressed: {sorted(licensed & failed)}"
    assert crr.main(["energydata-kit", "--root", str(REPO)]) == 0
    assert crr.main(["energydata-kit", "--strict", "--root", str(REPO)]) == 0
    assert crr.main(["energydata-kit", "--guard", "--root", str(REPO)]) == 0
