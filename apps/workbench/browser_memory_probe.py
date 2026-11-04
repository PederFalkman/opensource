"""WEB-10: optional browser process-tree memory telemetry for manual smoke gates.

This module never starts a browser, downloads a dependency, or reads customer data.
Requires optional psutil during actual process sampling. Values represent the
Python test driver's *descendant process tree* (Playwright driver + browser and
its subprocesses). They are not pure browser, worker, Pyodide, or WASM memory.
"""
from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from typing import Any

MAX_SAMPLES = 120_000


def process_tree_rss(root_pid: int, psutil_module: Any) -> tuple[int, int]:
    """Sum best-effort resident bytes across live child processes, not root.

    Excludes the test process itself. A changing process tree can produce
    incomplete instantaneous samples; no measurement is a memory leak proof.
    """
    if not isinstance(root_pid, int) or root_pid <= 0:
        raise ValueError("root_pid must be a positive PID")
    root = psutil_module.Process(root_pid)
    total = 0
    count = 0
    for child in root.children(recursive=True):
        try:
            if not child.is_running():
                continue
            rss = int(child.memory_info().rss)
            if rss < 0:
                continue
            total += rss
            count += 1
        except (psutil_module.NoSuchProcess, psutil_module.AccessDenied):
            continue
    return total, count


def process_tree_pss(root_pid: int, psutil_module: Any) -> dict[str, int | bool | None]:
    """Best-effort proportional set size for every live descendant.

    On systems without memory_full_info().pss, do not replace missing PSS with
    RSS or zero. Missing or denied process readings make total incomplete.
    """
    if not isinstance(root_pid, int) or root_pid <= 0:
        raise ValueError("root_pid must be a positive PID")
    root = psutil_module.Process(root_pid)
    count = 0
    measured = 0
    total = 0
    for child in root.children(recursive=True):
        try:
            if not child.is_running():
                continue
            count += 1
            value = getattr(child.memory_full_info(), "pss", None)
            if not isinstance(value, (int, float)) or value < 0:
                continue
            total += int(value)
            measured += 1
        except (psutil_module.NoSuchProcess, psutil_module.AccessDenied,
                AttributeError, NotImplementedError):
            continue
    complete = measured == count
    return {
        "pss_bytes": total if complete and measured else None,
        "processes_seen": count,
        "processes_with_pss": measured,
        "complete": complete and measured > 0,
    }


@dataclass(frozen=True)
class MemoryResult:
    samples: int
    peak_descendant_rss_bytes: int | None
    final_descendant_rss_bytes: int | None
    final_descendant_process_count: int | None
    interval_ms: int
    scope: str = "test-driver-descendants-including-playwright-and-browser"

    def to_dict(self) -> dict[str, Any]:
        return {
            "samples": self.samples,
            "peak_descendant_rss_bytes": self.peak_descendant_rss_bytes,
            "final_descendant_rss_bytes": self.final_descendant_rss_bytes,
            "final_descendant_process_count": self.final_descendant_process_count,
            "interval_ms": self.interval_ms,
            "scope": self.scope,
            "limitations": (
                "OS RSS summed across descendant processes; includes Playwright driver; "
                "shared memory may be counted repeatedly; sampled peak is not continuous; "
                "not equivalent to WASM linear memory or memory reclaimed by a single Worker."
            ),
        }


class MemorySampler:
    """Bounded periodic RSS sampler. Activate only in explicit manual benchmarks."""

    def __init__(self, psutil_module: Any, *, root_pid: int | None = None,
                 interval_ms: int = 100) -> None:
        if not 20 <= interval_ms <= 5000:
            raise ValueError("interval_ms must be in 20..5000")
        self.root_pid = os.getpid() if root_pid is None else root_pid
        if not isinstance(self.root_pid, int) or self.root_pid <= 0:
            raise ValueError("invalid root PID")
        self.psutil = psutil_module
        self.interval_ms = interval_ms
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._samples = 0
        self._peak: int | None = None
        self._final: int | None = None
        self._count: int | None = None
        self._lock = threading.Lock()
        self._failure: str | None = None

    def _run(self) -> None:
        while not self._stop.is_set() and self._samples < MAX_SAMPLES:
            try:
                rss, count = process_tree_rss(self.root_pid, self.psutil)
                with self._lock:
                    self._samples += 1
                    self._peak = rss if self._peak is None else max(self._peak, rss)
                    self._final = rss
                    self._count = count
            except self.psutil.NoSuchProcess:
                # The monitored child harness exited normally; this is not a
                # measurement failure and prior samples remain valid.
                break
            except self.psutil.AccessDenied as exc:
                self._failure = type(exc).__name__
                break
            self._stop.wait(self.interval_ms / 1000)

    def start(self) -> "MemorySampler":
        if self._thread is not None:
            raise RuntimeError("Memory sampler was already started")
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> MemoryResult:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=10)
            if self._thread.is_alive():
                raise RuntimeError("Memory sampling thread did not stop")
        if self._failure:
            raise RuntimeError(f"Process sampling failed: {self._failure}")
        with self._lock:
            return MemoryResult(
                samples=self._samples,
                peak_descendant_rss_bytes=self._peak,
                final_descendant_rss_bytes=self._final,
                final_descendant_process_count=self._count,
                interval_ms=self.interval_ms,
            )


def load_psutil() -> Any:
    """Import optional observer only when the manual benchmark requests it."""
    try:
        import psutil
    except ImportError as exc:
        raise RuntimeError(
            "Install optional memory benchmark dependency: python -m pip install psutil"
        ) from exc
    return psutil
