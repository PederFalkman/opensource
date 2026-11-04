"""Fast, no-browser tests for opt-in WEB-10 process memory observer."""
from __future__ import annotations

import importlib.util
import threading
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("web10_memory", HERE / "browser_memory_probe.py")
assert SPEC and SPEC.loader
memory = importlib.util.module_from_spec(SPEC)
import sys
sys.modules[SPEC.name] = memory
SPEC.loader.exec_module(memory)


class FakeNoSuchProcess(Exception):
    pass


class FakeAccessDenied(Exception):
    pass


class FakeChild:
    def __init__(self, rss: int, *, running: bool = True, exc=None):
        self.rss = rss
        self.running = running
        self.exc = exc

    def is_running(self):
        return self.running

    def memory_info(self):
        if self.exc:
            raise self.exc()
        return type("Info", (), {"rss": self.rss})()


class FakePsutil:
    NoSuchProcess = FakeNoSuchProcess
    AccessDenied = FakeAccessDenied
    _children = []

    @classmethod
    def Process(cls, pid):
        assert pid == 42
        return cls()

    def children(self, recursive=False):
        assert recursive
        return self.__class__._children


def test_process_tree_rss_skips_terminated_and_access_denied():
    FakePsutil._children = [
        FakeChild(500), FakeChild(100, running=False),
        FakeChild(3, exc=FakeAccessDenied), FakeChild(1500)
    ]
    assert memory.process_tree_rss(42, FakePsutil) == (2000, 2)


def test_invalid_root_or_interval():
    with pytest.raises(ValueError):
        memory.process_tree_rss(0, FakePsutil)
    with pytest.raises(ValueError):
        memory.MemorySampler(FakePsutil, root_pid=42, interval_ms=10)


def test_sampler_is_bounded_and_reports_scope_without_leak_claim():
    FakePsutil._children = [FakeChild(1234)]
    sampler = memory.MemorySampler(FakePsutil, root_pid=42, interval_ms=20)
    sampler.start()
    threading.Event().wait(0.06)
    result = sampler.stop()
    data = result.to_dict()
    assert data["samples"] >= 1
    assert data["peak_descendant_rss_bytes"] == 1234
    assert data["final_descendant_process_count"] == 1
    assert "not equivalent to WASM linear memory" in data["limitations"]
    with pytest.raises(RuntimeError, match="already started"):
        sampler.start()


def test_empty_sample_is_absent_not_zero():
    result = memory.MemoryResult(0, None, None, None, 100).to_dict()
    assert result["peak_descendant_rss_bytes"] is None
    assert result["final_descendant_rss_bytes"] is None

class FakePssChild(FakeChild):
    def __init__(self, pss, **kwargs):
        super().__init__(123, **kwargs)
        self.pss = pss

    def memory_full_info(self):
        return type("Full", (), {})() if self.pss is None else type(
            "Full", (), {"pss": self.pss}
        )()


def test_pss_complete_only_and_no_rss_fallback():
    FakePsutil._children = [FakePssChild(125), FakePssChild(225)]
    assert memory.process_tree_pss(42, FakePsutil) == {
        "pss_bytes": 350, "processes_seen": 2,
        "processes_with_pss": 2, "complete": True
    }
    FakePsutil._children = [FakePssChild(125), FakePssChild(None)]
    incomplete = memory.process_tree_pss(42, FakePsutil)
    assert incomplete["pss_bytes"] is None
    assert incomplete["processes_seen"] == 2
    assert incomplete["processes_with_pss"] == 1
    assert not incomplete["complete"]


def test_pss_unavailable_is_null_not_zero():
    FakePsutil._children = [FakeChild(234)]
    result = memory.process_tree_pss(42, FakePsutil)
    assert result["pss_bytes"] is None
    assert result["processes_with_pss"] == 0


def test_sampler_records_complete_pss_and_keeps_rss_distinct():
    FakePsutil._children = [FakePssChild(250), FakePssChild(350)]
    sampler = memory.MemorySampler(FakePsutil, root_pid=42, interval_ms=20)
    sampler.start()
    threading.Event().wait(0.06)
    result = sampler.stop().to_dict()
    assert result["samples"] >= 1
    assert result["complete_pss_samples"] >= 1
    assert result["peak_complete_pss_bytes"] == 600
    assert result["peak_descendant_rss_bytes"] == 246
