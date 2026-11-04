"""Offline checks of WEB-09 Linux RSS diagnostic accounting and limitations."""
from __future__ import annotations

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "web09_memory_probe", HERE / "web09_memory_probe.py"
)
assert SPEC and SPEC.loader
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


def fake_proc(root: Path, pid: int, ppid: int, rss_kb: int) -> None:
    entry = root / str(pid)
    entry.mkdir()
    (entry / "stat").write_text(
        f"{pid} (process with spaces) S {ppid} 1 1 0 0",
        encoding="utf-8",
    )
    (entry / "status").write_text(
        f"Name:\ttest\nVmRSS:\t{rss_kb} kB\n",
        encoding="utf-8",
    )


def test_sums_only_descendants_and_handles_parentheses(tmp_path: Path) -> None:
    fake_proc(tmp_path, 100, 1, 50)
    fake_proc(tmp_path, 101, 100, 25)
    fake_proc(tmp_path, 102, 101, 30)
    fake_proc(tmp_path, 999, 1, 10000)
    assert probe.process_tree_rss(100, tmp_path) == {
        "rss_sum_bytes": 105 * 1024,
        "process_count": 3,
        "rss_reported_process_count": 3,
    }


def test_missing_proc_and_exited_root_are_explicit_unknown(tmp_path: Path) -> None:
    assert probe.process_tree_rss(100, tmp_path) is None
    assert probe.process_tree_rss(100, tmp_path / "missing") is None


def test_incomplete_process_status_does_not_fabricate_rss(tmp_path: Path) -> None:
    fake_proc(tmp_path, 10, 1, 12)
    fake_proc(tmp_path, 11, 10, 7)
    (tmp_path / "11" / "status").unlink()
    assert probe.process_tree_rss(10, tmp_path) == {
        "rss_sum_bytes": 12 * 1024,
        "process_count": 2,
        "rss_reported_process_count": 1,
    }


def test_sampler_summary_never_claims_wasm_or_memory_reclamation() -> None:
    sampler = probe.ProcessTreeRssSampler()
    summary = sampler.summary()
    assert summary["sample_count"] == 0
    assert summary["sampled_peak_rss_sum_bytes"] is None
    assert "shared memory" in summary["caveat"]
    assert "Not WASM heap" in summary["caveat"]
