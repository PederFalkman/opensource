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
    license_field: bool = True,
    guard: bool = False,
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
        ({"license_field": False}, ["license declared"]),
        ({"guard": True}, ["upload guard removed"]),
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


def test_missing_package(tmp_path):
    assert failing(make_repo(tmp_path)) == []
    assert [c.name for c in crr.check_package(tmp_path, "absent")] == ["package exists"]


def test_real_repository_is_not_release_ready():
    # The gates are not passed yet: the real package must not look releasable.
    failed = {c.name for c in crr.check_package(REPO, "energydata-kit") if not c.ok}
    assert {"final version", "LICENSE file", "license declared", "upload guard removed"} <= failed
    assert crr.main(["energydata-kit", "--root", str(REPO)]) == 0
    assert crr.main(["energydata-kit", "--strict", "--root", str(REPO)]) == 1
