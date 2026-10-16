import importlib.util
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent
REPO = TOOLS.parent

spec = importlib.util.spec_from_file_location("check_docs", TOOLS / "check_docs.py")
assert spec and spec.loader
cd = importlib.util.module_from_spec(spec)
sys.modules["check_docs"] = cd
spec.loader.exec_module(cd)

INIT = '"""Demo."""\n__version__ = "0"\n__all__ = ["__version__", "alpha", "Beta"]\n'
FLAGS = (
    '"""Flags."""\nfrom enum import IntFlag\n'
    'class QualityFlag(IntFlag):\n    """Flags."""\n    OK = 0\n    BAD = 1\n'
)
README = "# demo\n\nUse `alpha` and `Beta`.\n\n| `OK` | `BAD` |\n\nSee [docs](docs/guide.md).\n"


def make_repo(tmp_path: Path, readme: str = README, changelog: str = "## [Unreleased]\n") -> Path:
    pkg = tmp_path / "packages" / "demo"
    src = pkg / "src" / "demo"
    src.mkdir(parents=True)
    (pkg / "pyproject.toml").write_text('[project]\nname = "demo"\n')
    (src / "__init__.py").write_text(INIT)
    (src / "flags.py").write_text(FLAGS)
    (pkg / "README.md").write_text(readme)
    (pkg / "CHANGELOG.md").write_text("# Changelog\n\n" + changelog)
    (pkg / "docs").mkdir()
    (pkg / "docs" / "guide.md").write_text("# guide\n")
    return tmp_path


def messages(root: Path) -> list[str]:
    return [p.message for p in cd.run(root)]


def test_consistent_repo_passes(tmp_path):
    assert messages(make_repo(tmp_path)) == []


def test_undocumented_public_name(tmp_path):
    msgs = messages(make_repo(tmp_path, readme=README.replace(" and `Beta`", "")))
    assert len(msgs) == 1 and "'Beta'" in msgs[0]


def test_name_must_match_as_a_whole_word(tmp_path):
    # "alphabet" must not count as a mention of "alpha".
    msgs = messages(make_repo(tmp_path, readme=README.replace("`alpha`", "alphabet")))
    assert len(msgs) == 1 and "'alpha'" in msgs[0]


def test_undocumented_flag(tmp_path):
    msgs = messages(make_repo(tmp_path, readme=README.replace("`BAD`", "")))
    assert msgs == ["QualityFlag.BAD missing from the flag table"]


def test_changelog_needs_unreleased(tmp_path):
    msgs = messages(make_repo(tmp_path, changelog="## [0.1.0] - 2026-01-01\n"))
    assert msgs == ["needs an '## [Unreleased]' section"]


def test_links(tmp_path):
    readme = README + (
        "[gone](missing.md) [ok](docs/guide.md#top) [web](https://example.com) "
        "[mail](mailto:a@b.c) [anchor](#x)\n\n```\n[in code](nowhere.md)\n```\n"
    )
    msgs = messages(make_repo(tmp_path, readme=readme))
    assert len(msgs) == 1 and "broken link 'missing.md'" in msgs[0]


def test_docstrings(tmp_path):
    root = make_repo(tmp_path)
    src = root / "packages" / "demo" / "src" / "demo"
    (src / "api.py").write_text(
        '''"""API."""


def documented():
    """Yes."""


def undocumented():
    pass


def _private():
    pass


class Thing:
    """A thing."""

    def method(self):
        pass

    @property
    def size(self):
        """Size."""
        return 1
'''
    )
    (src / "bare.py").write_text("x = 1\n")
    messages = sorted(p.message for p in cd.run(root))
    assert messages == [
        "<module> has no docstring",
        "Thing.method has no docstring",
        "undocumented has no docstring",
    ]


def test_real_repository_passes():
    assert cd.run(REPO) == []
