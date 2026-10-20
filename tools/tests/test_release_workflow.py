"""The release workflow's GitHub-release step (P-11, OSS-101).

The step's shell script is run with a fake ``gh`` on ``PATH`` that records its
calls, so the three paths are exercised without GitHub: a new tag gets a
draft release, a draft gets its files replaced, and a published release is
never changed. Standard library only; needs ``bash``.
"""

import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
WORKFLOW = REPO / ".github" / "workflows" / "release-build.yml"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")


def job(name: str) -> str:
    """The text of one job in the workflow (up to the next top-level job)."""
    text = WORKFLOW.read_text()
    match = re.search(rf"^  {re.escape(name)}:\n(.*?)(?=^  \S|\Z)", text, re.MULTILINE | re.DOTALL)
    assert match, name
    return match.group(1)


def release_script() -> str:
    body = job("github-release")
    run = body.split("run: |\n", 1)[1]
    return "\n".join(line[10:] for line in run.splitlines())


def run_step(tmp_path: Path, existing: str | None) -> tuple[int, list[str], str]:
    """Run the step; ``existing`` is None (no release), "true" (draft) or "false"."""
    (tmp_path / "dist").mkdir()
    for name in ("energydata_kit-0.2.0-py3-none-any.whl", "energydata_kit-0.2.0.tar.gz"):
        (tmp_path / "dist" / name).write_bytes(name.encode())
    log = tmp_path / "gh.log"
    fake = tmp_path / "bin" / "gh"
    fake.parent.mkdir()
    view = f"echo {existing}; exit 0" if existing else "exit 1"
    fake.write_text(
        f'#!/usr/bin/env bash\necho "$*" >> "{log}"\nif [ "$1 $2" = "release view" ]; then {view}; fi\n'
    )
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    env = {
        **os.environ,
        "PATH": f"{fake.parent}{os.pathsep}{os.environ['PATH']}",
        "TAG": "energydata-kit-v0.2.0",
    }
    result = subprocess.run(
        ["bash", "-e", "-c", release_script()], cwd=tmp_path, env=env, capture_output=True, text=True
    )
    calls = log.read_text().splitlines() if log.exists() else []
    return result.returncode, calls, result.stdout + result.stderr


def test_new_tag_gets_a_draft_release_with_files_and_sums(tmp_path):
    code, calls, _ = run_step(tmp_path, existing=None)
    assert code == 0
    create = calls[-1]
    assert create.startswith("release create energydata-kit-v0.2.0 ")
    assert "--draft" in create and "--verify-tag" in create
    for name in ("energydata_kit-0.2.0-py3-none-any.whl", "energydata_kit-0.2.0.tar.gz", "SHA256SUMS"):
        assert f"dist/{name}" in create
    sums = (tmp_path / "dist" / "SHA256SUMS").read_text()
    assert "energydata_kit-0.2.0.tar.gz" in sums and "SHA256SUMS" not in sums


def test_draft_release_gets_its_files_replaced(tmp_path):
    code, calls, _ = run_step(tmp_path, existing="true")
    assert code == 0
    assert calls[-1].startswith("release upload energydata-kit-v0.2.0 ") and "--clobber" in calls[-1]


def test_published_release_is_never_changed(tmp_path):
    code, calls, out = run_step(tmp_path, existing="false")
    assert code == 1 and "already published" in out
    assert not any(c.startswith(("release upload", "release create")) for c in calls)


def test_only_the_release_job_may_write_and_nothing_goes_to_an_index():
    text = WORKFLOW.read_text()
    assert re.search(r"^permissions:\n  contents: read\n", text, re.MULTILINE)
    assert text.count("contents: write") == 1 and "contents: write" in job("github-release")
    body = job("github-release")
    assert "needs: [build, attest]" in body
    assert "startsWith(github.ref, 'refs/tags/energydata-kit-v')" in body
    for word in ("twine upload", "pypi", "PYPI", "gh-action-pypi-publish"):
        assert word not in text
