import importlib.util
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent
REPO = TOOLS.parent

spec = importlib.util.spec_from_file_location("check_third_party", TOOLS / "check_third_party.py")
assert spec and spec.loader
ctp = importlib.util.module_from_spec(spec)
sys.modules["check_third_party"] = ctp
spec.loader.exec_module(ctp)

PYPROJECT = """
[build-system]
requires = ["hatchling>=1.24"]

[project]
name = "demo"
dependencies = ["numpy>=1.26", "Pandas_Extra>=1"]

[project.optional-dependencies]
fancy = ["pandera>=0.24"]

[dependency-groups]
dev = ["pytest>=8", "pandera>=0.24", {include-group = "other"}]
"""

ROWS = [
    "| `numpy` | runtime | BSD-3-Clause | yes | metadata |",
    "| `pandas-extra` | runtime | MIT | yes | metadata |",
    "| `pandera` | extra:fancy, dev | MIT | extra | metadata |",
    "| `hatchling` | build | MIT | no | PyPI |",
    "| `pytest` | dev | MIT | no | metadata |",
]


def make_repo(tmp_path: Path, rows: list[str] = ROWS) -> Path:
    pkg = tmp_path / "packages" / "demo"
    pkg.mkdir(parents=True)
    (pkg / "pyproject.toml").write_text(PYPROJECT)
    doc = tmp_path / ctp.DOC_PATH
    doc.parent.mkdir(parents=True)
    table = "\n".join(["| Package | Scopes | Licence | Shipped | Source |", "|---|---|---|---|---|", *rows])
    other = "## Other\n\n| `numpy` | x | y |\n"  # rows outside the table are ignored
    doc.write_text(f"# Licences\n\n## Direct dependencies of `demo`\n\n{table}\n\n{other}")
    return tmp_path


def messages(root: Path) -> list[str]:
    return [p.message for p in ctp.run(root)]


def test_repository_is_clean():
    assert ctp.run(REPO) == []


def test_matching_table_passes(tmp_path):
    assert messages(make_repo(tmp_path)) == []


def test_missing_and_extra_rows(tmp_path):
    rows = [r for r in ROWS if "pytest" not in r] + ["| `requests` | runtime | Apache-2.0 | yes | x |"]
    assert messages(make_repo(tmp_path, rows)) == [
        "demo: dependency 'pytest' has no row",
        "demo: row 'requests' is not a declared dependency",
    ]


def test_scope_mismatch_and_missing_licence(tmp_path):
    rows = [r.replace("extra:fancy, dev", "dev") for r in ROWS]
    rows = [r.replace("| build | MIT |", "| build |  |") for r in rows]
    assert messages(make_repo(tmp_path, rows)) == [
        "demo: 'pandera' scopes are ['dev'], declared as ['dev', 'extra:fancy']",
        "demo: 'hatchling' has no licence",
    ]


def test_copyleft_only_rejected_when_shipped(tmp_path):
    rows = [r.replace("| runtime | MIT |", "| runtime | GPL-3.0-only |") for r in ROWS]
    rows = [r.replace("| dev | MIT |", "| dev | MPL-2.0 |") for r in rows]
    assert messages(make_repo(tmp_path, rows)) == [
        "demo: shipped dependency 'pandas-extra' is copyleft (GPL-3.0-only)"
    ]
    rows = [r.replace("| runtime | MIT |", "| runtime | LGPL-3.0-only OR MIT |") for r in ROWS]
    assert messages(make_repo(tmp_path / "choice", rows)) == []


def test_missing_doc_or_table(tmp_path):
    root = make_repo(tmp_path)
    doc = root / ctp.DOC_PATH
    doc.write_text("# Licences\n")
    assert messages(root) == ["no 'Direct dependencies of `demo`' table"]
    doc.unlink()
    assert messages(root) == ["missing"]


def test_report_lists_installed_dependencies():
    # pytest is installed wherever these tests run; pluggy is one of its dependencies.
    rows = ctp.report("pytest")
    assert any(r.startswith("| `pluggy` | pytest | MIT") for r in rows), rows
    assert not any(r.startswith("| `pytest` |") for r in rows)
