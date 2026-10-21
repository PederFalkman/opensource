"""Time energydata-kit on long synthetic series.

Usage: ``python benchmarks/run.py`` (from ``packages/energydata-kit``, with the
package installed). Prints wall time and peak traced memory per case. The
numbers depend on the machine; compare runs on the same machine only.
Results for the 0.1.0 candidate are in docs/architecture/PERFORMANCE.md.
"""

from __future__ import annotations

import platform
import time
import tracemalloc
from collections.abc import Callable

import numpy as np
import pandas as pd

import energydata_kit as ek


def series(n: int, freq: str, seed: int = 0, defects: bool = True) -> pd.Series:
    """Synthetic values; with defects, 0.1 % of rows dropped and 0.1 % NaN."""
    rng = np.random.default_rng(seed)
    index = pd.date_range("2020-01-01", periods=n, freq=freq, tz="UTC")
    s = pd.Series(rng.normal(100.0, 5.0, n), index=index, name=f"x{seed}")
    if defects:
        s = s.drop(s.index[rng.choice(n, n // 1000, replace=False)])
        s.iloc[rng.choice(len(s), len(s) // 1000, replace=False)] = np.nan
    return s


def measure(label: str, fn: Callable[[], object], repeat: int = 3) -> None:
    # Time without tracemalloc, which slows Python-level code many times over and
    # would distort the timings (OSS-136); trace memory in one extra run.
    times = []
    for _ in range(repeat):
        start = time.perf_counter()
        fn()
        times.append(time.perf_counter() - start)
    tracemalloc.start()
    fn()
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    print(f"| {label} | {min(times):.2f} | {peak / 2**20:.0f} |", flush=True)


def main() -> None:
    print(
        f"energydata-kit {ek.__version__}, Python {platform.python_version()}, "
        f"pandas {pd.__version__}, numpy {np.__version__}, {platform.machine()}"
    )
    minute = series(525_600, "1min")  # one year at 1 min
    quarter = series(350_640, "15min")  # ten years at 15 min
    frame = pd.DataFrame({f"c{i}": series(350_640, "15min", seed=i, defects=False) for i in range(5)})
    strings = pd.Series(pd.date_range("2020-01-01", periods=350_640, freq="15min").astype(str))
    local = pd.date_range("2020-01-01", periods=350_640, freq="15min", tz="Europe/Stockholm")
    offset_strings = pd.Series([t.isoformat() for t in local])  # +01:00 / +02:00 across DST
    compact_offsets = pd.Series([t.strftime("%Y-%m-%dT%H:%M:%S%z") for t in local])  # +0100 / +0200
    every_check = {"bounds": (0, 200), "stale_min_run": 5, "cumulative": True, "jump_max_delta": 50}

    print("\n| Case (best of 3) | Time (s) | Peak traced memory (MiB) |\n|---|---|---|")
    measure(
        "`normalize_timestamps`, 350k naive ISO strings",
        lambda: ek.normalize_timestamps(strings, assume_tz="UTC"),
    )
    measure(
        "`normalize_timestamps`, 350k ISO strings with DST offsets",
        lambda: ek.normalize_timestamps(offset_strings),
    )
    measure(
        "`normalize_timestamps`, 350k ISO strings with DST offsets as `+0100`",
        lambda: ek.normalize_timestamps(compact_offsets),
    )
    measure("`flag_series`, 1 year at 1 min", lambda: ek.flag_series(minute, freq="1min"))
    measure(
        "`flag_series`, 1 year at 1 min, every check + `insert_missing`",
        lambda: ek.flag_series(minute, freq="1min", insert_missing=True, **every_check),
    )
    measure(
        "`find_missing_intervals`, 1 year at 1 min", lambda: ek.find_missing_intervals(minute.index, "1min")
    )
    measure("`assess_quality`, 1 year at 1 min", lambda: ek.assess_quality(minute, freq="1min"))
    measure(
        "`assess_quality`, 10 years at 15 min, every check",
        lambda: ek.assess_quality(quarter, freq="15min", **every_check),
    )
    measure(
        "`local_day_completeness`, 10 years at 15 min, Europe/Stockholm",
        lambda: ek.local_day_completeness(quarter.index, "15min", "Europe/Stockholm"),
    )
    measure("`assess_frame`, 5 columns, 10 years at 15 min", lambda: ek.assess_frame(frame, freq="15min"))


if __name__ == "__main__":
    main()
