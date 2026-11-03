"""WEB-02: local, authoritative EnergyData Kit report adapter.

Usage:
    python apps/workbench/python_report.py readings.csv --timestamp timestamp --value value --interval-minutes 15

This is a CLI, not an HTTP server. Data stays on the user's computer.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

MAX_BYTES = 5 * 1024 * 1024
OFFSET = re.compile(r"(?:Z|[+-][0-9]{2}:[0-9]{2})$", re.IGNORECASE)


def analyze_csv(
    path: Path,
    *,
    timestamp: str = "timestamp",
    value: str = "value",
    interval_minutes: int = 15,
) -> dict[str, object]:
    import pandas as pd
    import energydata_kit as ek

    if not 1 <= interval_minutes <= 1440:
        raise ValueError("interval_minutes must be between 1 and 1440")
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError("CSV must exist and be at most 5 MiB")
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    if frame.empty or not frame.columns.is_unique:
        raise ValueError("CSV must have rows and unique column names")
    if timestamp == value or timestamp not in frame or value not in frame:
        raise ValueError("choose two distinct, existing timestamp and value columns")
    raw_times = frame[timestamp].astype(str).str.strip()
    if not raw_times.map(lambda x: bool(OFFSET.search(x))).all():
        raise ValueError("every timestamp must include UTC offset or Z; no implicit DST assumptions")
    parsed = pd.to_datetime(raw_times, utc=True, errors="raise")
    numeric = pd.to_numeric(frame[value].replace("", float("nan")), errors="coerce")
    series = pd.Series(numeric.to_numpy(), index=pd.DatetimeIndex(parsed), name=value)
    canonical = ek.assess_quality(series, freq=f"{interval_minutes}min")
    return {
        "adapter_version": "energydata.workbench.python.v1",
        "engine": "python-validated",
        "package_version": ek.__version__,
        "source": path.name,
        "columns": {"timestamp": timestamp, "value": value},
        "interval_minutes": interval_minutes,
        "report": canonical.to_dict(),
        "privacy": "local-file-only",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--timestamp", default="timestamp")
    parser.add_argument("--value", default="value")
    parser.add_argument("--interval-minutes", type=int, default=15)
    parser.add_argument("--output", type=Path, help="Optional local JSON destination")
    args = parser.parse_args(argv)
    try:
        report = analyze_csv(
            args.csv, timestamp=args.timestamp, value=args.value,
            interval_minutes=args.interval_minutes,
        )
        payload = json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
        if args.output:
            args.output.write_text(payload + "\n", encoding="utf-8")
        else:
            print(payload)
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"Data assessment failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
