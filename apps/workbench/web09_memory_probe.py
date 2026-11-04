"""Linux-only WEB-09 process-tree RSS sampler for manual browser smoke tests.

All values are sampled sums of per-process VmRSS. Shared pages may be counted
multiple times; it includes the test runner and Playwright driver descendants.
This is not Python/WASM heap usage, USS/PSS, peak resident memory or a proof
of memory reclamation after a Worker is terminated.
"""
from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any


def process_tree_rss(root_pid: int, proc_root: Path = Path("/proc")) -> dict[str, int] | None:
    """Return sampled RSS summed over the root process and live descendants."""
    if not proc_root.is_dir():
        return None
    parent_by_pid: dict[int, int] = {}
    resident_by_pid: dict[int, int] = {}
    try:
        entries = list(proc_root.iterdir())
    except OSError:
        return None
    for entry in entries:
        if not entry.name.isdigit() or not entry.is_dir():
            continue
        pid = int(entry.name)
        try:
            stat_text = (entry / "stat").read_text(encoding="utf-8")
            tail = stat_text[stat_text.rfind(")") + 1:].split()
            if len(tail) < 2:
                continue
            parent_by_pid[pid] = int(tail[1])
            for line in (entry / "status").read_text(encoding="utf-8").splitlines():
                if line.startswith("VmRSS:"):
                    resident_by_pid[pid] = int(line.split()[1]) * 1024
                    break
        except (OSError, ValueError, IndexError):
            # Process may exit while /proc is being sampled.
            continue
    if root_pid not in parent_by_pid:
        return None
    included = {root_pid}
    while True:
        additions = {
            pid for pid, parent in parent_by_pid.items()
            if parent in included and pid not in included
        }
        if not additions:
            break
        included.update(additions)
    return {
        "rss_sum_bytes": sum(resident_by_pid.get(pid, 0) for pid in included),
        "process_count": len(included),
        "rss_reported_process_count": sum(pid in resident_by_pid for pid in included),
    }


class ProcessTreeRssSampler:
    """Sample the full runner process tree without retaining process identifiers."""

    def __init__(self, *, interval_seconds: float = 0.2) -> None:
        self.interval_seconds = interval_seconds
        self.root_pid = os.getpid()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._samples = 0
        self._max_bytes = 0
        self._max_process_count = 0

    def snapshot(self) -> dict[str, int] | None:
        result = process_tree_rss(self.root_pid)
        if result is not None:
            with self._lock:
                self._samples += 1
                self._max_bytes = max(self._max_bytes, result["rss_sum_bytes"])
                self._max_process_count = max(
                    self._max_process_count, result["process_count"]
                )
        return result

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError("Sampler already started")
        self.snapshot()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            self.snapshot()

    def summary(self) -> dict[str, Any]:
        with self._lock:
            return {
                "kind": "linux_proc_runner_process_tree_sum_vmrss",
                "sample_interval_ms": round(self.interval_seconds * 1000),
                "sample_count": self._samples,
                "sampled_peak_rss_sum_bytes": self._max_bytes or None,
                "max_process_count": self._max_process_count,
                "caveat": (
                    "Includes Python harness, Playwright driver and browser children; "
                    "shared memory can be double counted. Not WASM heap, USS/PSS, "
                    "actual peak RSS or proof that Worker memory was reclaimed."
                ),
            }

    def stop(self) -> dict[str, Any]:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
        self.snapshot()
        return self.summary()
