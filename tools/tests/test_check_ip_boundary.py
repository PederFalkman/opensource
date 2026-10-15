import importlib.util
import sys
import textwrap
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent.parent
REPO = TOOLS.parent

spec = importlib.util.spec_from_file_location("check_ip_boundary", TOOLS / "check_ip_boundary.py")
assert spec and spec.loader
cib = importlib.util.module_from_spec(spec)
sys.modules["check_ip_boundary"] = cib
spec.loader.exec_module(cib)

CONFIG = """
forbidden_imports = ["mica", "rodot"]
[allowed_dependencies]
demo = ["hatchling", "numpy", "pytest"]
"""


def make_repo(tmp_path: Path, deps: str = '["numpy>=1"]', group: str = '["pytest"]', code: str = "") -> Path:
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "ip_boundary.toml").write_text(CONFIG)
    pkg = tmp_path / "packages" / "demo"
    (pkg / "src" / "demo").mkdir(parents=True)
    (pkg / "pyproject.toml").write_text(
        textwrap.dedent(f"""
        [build-system]
        requires = ["hatchling>=1.24"]
        [project]
        name = "demo"
        dependencies = {deps}
        [dependency-groups]
        dev = {group}
        """)
    )
    (pkg / "src" / "demo" / "__init__.py").write_text(code)
    return tmp_path


def messages(root: Path) -> list[str]:
    return [v.message for v in cib.run(root)]


def test_clean_repo_passes(tmp_path):
    assert messages(make_repo(tmp_path, code="import numpy\nfrom pandas import Series\n")) == []


@pytest.mark.parametrize(
    "code",
    [
        "import mica",
        "import mica.models",
        "from rodot.core import x",
        "import mica_internal",
        "import importlib\nimportlib.import_module('rodot')",
        "__import__('MICA')",
    ],
)
def test_forbidden_imports(tmp_path, code):
    msgs = messages(make_repo(tmp_path, code=code))
    assert len(msgs) == 1 and "forbidden import" in msgs[0]


def test_similar_names_allowed(tmp_path):
    assert messages(make_repo(tmp_path, code="import micado\nimport rodotx\nfrom . import mica\n")) == []


def test_unlisted_dependency(tmp_path):
    msgs = messages(make_repo(tmp_path, deps='["numpy", "requests"]'))
    assert msgs == ["dependency 'requests' is not in the allowlist (tools/ip_boundary.toml)"]


def test_unlisted_dev_dependency(tmp_path):
    assert len(messages(make_repo(tmp_path, group='["pytest", "hypothesis"]'))) == 1


@pytest.mark.parametrize(
    "dep", ['"numpy @ git+ssh://git@github.com/x/y.git"', '"numpy @ https://example.com/n.whl"']
)
def test_direct_references_rejected(tmp_path, dep):
    msgs = messages(make_repo(tmp_path, deps=f"[{dep}]"))
    assert len(msgs) == 1 and "direct/VCS" in msgs[0]


def test_package_without_allowlist(tmp_path):
    root = make_repo(tmp_path)
    (root / "tools" / "ip_boundary.toml").write_text("forbidden_imports = []\n[allowed_dependencies]\n")
    assert "has no allowlist" in messages(root)[0]


def test_real_repository_passes():
    assert cib.run(REPO) == []
