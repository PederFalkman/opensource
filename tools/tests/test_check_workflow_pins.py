import importlib.util
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent.parent
REPO = TOOLS.parent

spec = importlib.util.spec_from_file_location("check_workflow_pins", TOOLS / "check_workflow_pins.py")
assert spec and spec.loader
cwp = importlib.util.module_from_spec(spec)
sys.modules["check_workflow_pins"] = cwp
spec.loader.exec_module(cwp)

SHA = "3d3c42e5aac5ba805825da76410c181273ba90b1"


def messages(text: str) -> list[str]:
    return [v.message for v in cwp.check_text(text, Path("wf.yml"))]


@pytest.mark.parametrize(
    "line",
    [
        f"      - uses: actions/checkout@{SHA} # v7.0.1",
        f"    uses: actions/checkout@{SHA}  #v7",
        f'      - uses: "github/codeql-action/init@{SHA}" # v3.1.0',
        "      - uses: ./.github/actions/local",
        "      - uses: docker://alpine@sha256:" + "a" * 64,
        "        run: echo uses: actions/checkout@v4",  # not a uses: key
    ],
)
def test_allowed(line):
    assert messages(line) == []


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("      - uses: actions/checkout@v4", "not pinned to a full commit SHA"),
        ("      - uses: actions/checkout@main # v4", "not pinned to a full commit SHA"),
        (f"      - uses: actions/checkout@{SHA[:7]} # v7", "not pinned to a full commit SHA"),
        (f"      - uses: actions/checkout@{SHA}", "needs a version comment"),
        (f"      - uses: actions/checkout@{SHA} # pinned", "needs a version comment"),
        ("      - uses: docker://alpine:3.20", "sha256 digest"),
        ("      - uses: checkout", "unrecognised"),
    ],
)
def test_rejected(line, expected):
    msgs = messages(line)
    assert len(msgs) == 1 and expected in msgs[0]


def test_reports_line_numbers(tmp_path):
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "ci.yml").write_text(f"jobs:\n  a:\n    steps:\n      - uses: actions/checkout@{SHA} # v7.0.1\n")
    (wf / "bad.yaml").write_text("jobs:\n  a:\n    steps:\n      - uses: actions/setup-python@v7\n")
    violations = cwp.run(tmp_path)
    assert [(str(v.path), v.line) for v in violations] == [(".github/workflows/bad.yaml", 4)]


def test_no_workflows_is_an_error(tmp_path):
    assert cwp.main(["x", str(tmp_path)]) == 1


def test_real_repository_is_pinned():
    assert cwp.workflow_files(REPO)
    assert cwp.run(REPO) == []
