"""Command-line interface: ``energydata-kit report data.csv ...``.

Reads one timestamp column and one value column from a CSV file, runs
:func:`energydata_kit.assess_quality` and prints the deterministic JSON report.
Optionally writes the non-destructive flagged table from
:func:`energydata_kit.flag_series`. With several ``--value-col`` options it
runs :func:`energydata_kit.assess_frame` and prints one report with a section
per column. ``energydata-kit compare before.json after.json`` prints what
changed between two saved reports (:func:`energydata_kit.compare_reports`).

Exit codes: 0 success; 1 ``--fail-on-issues`` and issues were found (or, for
``compare``, ``--fail-if-worse`` and the second report is worse); 2 usage,
input or data error.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

import pandas as pd

from energydata_kit import __version__
from energydata_kit.compare import compare_reports
from energydata_kit.flags import VALUE_COLUMN, flag_series
from energydata_kit.frame_report import FrameQualityReport, assess_frame
from energydata_kit.metadata import Aggregation, IntervalLabel, MeasurementMetadata
from energydata_kit.report import QualityReport, assess_quality
from energydata_kit.timestamps import TimestampError, normalize_timestamps

__all__ = ["build_parser", "main"]

PROG = "energydata-kit"


class CliError(Exception):
    """An input or data problem reported to the user without a traceback."""


def _bound(text: str) -> float | None:
    if text.lower() in {"none", "-", ""}:
        return None
    try:
        return float(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"bound must be a number or 'none', got {text!r}") from exc


def _positive_int(text: str) -> int:
    value = int(text)
    if value < 0:
        raise argparse.ArgumentTypeError("must be >= 0")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=PROG, description="Quality checks for energy time-series data.")
    parser.add_argument("--version", action="version", version=f"{PROG} {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    rep = sub.add_parser(
        "report",
        help="print a JSON quality report for a CSV file",
        description="Print a deterministic JSON quality report for value columns of a CSV file.",
    )
    rep.add_argument("csv", help="input CSV file, or '-' for standard input")

    cols = rep.add_argument_group("columns")
    cols.add_argument("--timestamp-col", default="timestamp", help="timestamp column (default: timestamp)")
    cols.add_argument(
        "--value-col",
        action="append",
        help="value column; repeat for a multi-column report (default: the only other column)",
    )

    ts = rep.add_argument_group("timestamps")
    ts.add_argument("--assume-tz", help="IANA zone for naive timestamps, e.g. Europe/Stockholm")
    ts.add_argument("--ambiguous", choices=["raise", "infer"], default="raise", help="DST fall-back policy")
    ts.add_argument(
        "--nonexistent",
        choices=["raise", "shift_forward", "shift_backward"],
        default="raise",
        help="DST spring-forward policy",
    )

    grid = rep.add_argument_group("grid")
    grid.add_argument("--freq", help="expected step, e.g. 15min, 1h; with --tz also D, W-MON, MS")
    grid.add_argument("--tz", help="treat --freq as a local-calendar step in this zone")
    grid.add_argument("--origin", help="timezone-aware timestamp the grid runs through")

    checks = rep.add_argument_group("checks")
    checks.add_argument(
        "--bounds",
        nargs=2,
        type=_bound,
        metavar=("LOWER", "UPPER"),
        help="plausibility range; use 'none' for an open side",
    )
    checks.add_argument("--stale-min-run", type=int, help="flag runs of at least N repeated values")
    checks.add_argument(
        "--stale-atol", type=float, default=0.0, help="values within this of each other count as repeated"
    )
    checks.add_argument(
        "--stale-exclude", type=float, nargs="+", default=[], metavar="VALUE", help="never flag runs of these"
    )
    checks.add_argument("--cumulative", action="store_true", help="treat values as a cumulative counter")
    checks.add_argument(
        "--counter-tolerance", type=float, default=0.0, help="ignore counter decreases up to this size"
    )
    checks.add_argument(
        "--jump-max-delta", type=float, help="flag changes larger than this from the previous value"
    )

    meta = rep.add_argument_group("measurement metadata (enabled by --unit)")
    meta.add_argument("--unit", help="unit, e.g. kW or kWh; adds metadata to the report")
    meta.add_argument("--resolution", help="metadata resolution (default: --freq)")
    meta.add_argument("--aggregation", choices=[a.value for a in Aggregation], default="instantaneous")
    meta.add_argument("--interval-label", choices=[lab.value for lab in IntervalLabel], default="start")
    meta.add_argument("--timezone", default=None, help="metadata time zone (default: --tz, else UTC)")

    out = rep.add_argument_group("output")
    out.add_argument("-o", "--output", help="write the JSON report here instead of standard output")
    out.add_argument("--flags-csv", help="also write value and quality_flag columns to this CSV")
    out.add_argument("--insert-missing", action="store_true", help="add rows for absent grid timestamps")
    out.add_argument("--max-listed", type=_positive_int, default=100, help="cap on listed gaps/duplicates")
    out.add_argument(
        "--fail-on-issues",
        action="store_true",
        help="exit with status 1 if any row is flagged or any interval is missing",
    )

    cmp = sub.add_parser(
        "compare",
        help="print what changed between two saved JSON reports",
        description="Print a deterministic JSON comparison of two reports written by 'report'.",
    )
    cmp.add_argument("before", help="earlier report (JSON)")
    cmp.add_argument("after", help="later report (JSON)")
    cmp.add_argument("-o", "--output", help="write the comparison here instead of standard output")
    cmp.add_argument(
        "--fail-if-worse",
        action="store_true",
        help="exit with status 1 if more rows are flagged, more intervals are missing or completeness fell",
    )
    return parser


def _read_frame(args: argparse.Namespace, stdin: TextIO) -> pd.DataFrame:
    source = stdin if args.csv == "-" else args.csv
    try:
        frame = pd.read_csv(source, dtype={args.timestamp_col: str}, keep_default_na=True)
    except FileNotFoundError as exc:
        raise CliError(f"file not found: {args.csv}") from exc
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
        raise CliError(f"could not read CSV: {exc}") from exc

    if args.timestamp_col not in frame.columns:
        raise CliError(f"timestamp column {args.timestamp_col!r} not found; columns: {list(frame.columns)}")
    value_cols = args.value_col
    if value_cols is None:
        others = [c for c in frame.columns if c != args.timestamp_col]
        if len(others) != 1:
            raise CliError(f"pass --value-col; candidate columns: {others}")
        value_cols = others
    for col in value_cols:
        if col not in frame.columns:
            raise CliError(f"value column {col!r} not found; columns: {list(frame.columns)}")
    if len(set(value_cols)) != len(value_cols):
        raise CliError("each --value-col may be given only once")

    try:
        index = normalize_timestamps(
            frame[args.timestamp_col],
            assume_tz=args.assume_tz,
            ambiguous=args.ambiguous,
            nonexistent=args.nonexistent,
        )
    except TimestampError as exc:
        message = (
            str(exc)
            .replace("pass assume_tz", "pass --assume-tz")
            .replace("assume_tz was given", "--assume-tz was given")
        )
        raise CliError(message) from exc
    return pd.DataFrame({str(c): frame[c].to_numpy() for c in value_cols}, index=index)


def _metadata(args: argparse.Namespace, name: str) -> MeasurementMetadata | None:
    if args.unit is None:
        return None
    return MeasurementMetadata(
        name=name,
        unit=args.unit,
        resolution=args.resolution or args.freq,
        aggregation=Aggregation(args.aggregation),
        interval_label=IntervalLabel(args.interval_label),
        timezone=args.timezone or args.tz or "UTC",
    )


def _has_issues(report: QualityReport | FrameQualityReport) -> bool:
    return report.n_flagged_rows > 0 or report.n_missing_intervals > 0


def _run_report(args: argparse.Namespace, stdin: TextIO, stdout: TextIO) -> int:
    if args.tz and not args.freq:
        raise CliError("--tz needs --freq")
    if args.insert_missing and not args.flags_csv:
        raise CliError("--insert-missing only affects --flags-csv")

    frame = _read_frame(args, stdin)
    origin = None if args.origin is None else pd.Timestamp(args.origin)
    bounds = None if args.bounds is None else (args.bounds[0], args.bounds[1])
    if frame.shape[1] > 1:
        return _run_frame_report(args, frame, origin, bounds, stdout)

    series = frame.iloc[:, 0]
    metadata = _metadata(args, str(series.name))
    report = assess_quality(
        series,
        metadata=metadata,
        freq=args.freq,
        bounds=bounds,
        stale_min_run=args.stale_min_run,
        stale_atol=args.stale_atol,
        stale_exclude=args.stale_exclude,
        cumulative=args.cumulative,
        counter_tolerance=args.counter_tolerance,
        jump_max_delta=args.jump_max_delta,
        origin=origin,
        tz=args.tz,
        max_listed=args.max_listed,
    )
    _write_report(args, report, stdout)

    if args.flags_csv:
        freq = args.freq if args.freq else (metadata.resolution if metadata else None)
        flagged = flag_series(
            series,
            freq=freq,
            bounds=bounds,
            insert_missing=args.insert_missing,
            stale_min_run=args.stale_min_run,
            stale_atol=args.stale_atol,
            stale_exclude=args.stale_exclude,
            cumulative=args.cumulative,
            counter_tolerance=args.counter_tolerance,
            jump_max_delta=args.jump_max_delta,
            origin=origin,
            tz=args.tz,
        )
        flagged = flagged.rename(columns={VALUE_COLUMN: series.name})
        flagged.index.name = args.timestamp_col
        flagged.to_csv(args.flags_csv, date_format="%Y-%m-%dT%H:%M:%S%z")

    return 1 if args.fail_on_issues and _has_issues(report) else 0


def _write_report(
    args: argparse.Namespace, report: QualityReport | FrameQualityReport, stdout: TextIO
) -> None:
    text = report.to_json() + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        stdout.write(text)


def _run_frame_report(
    args: argparse.Namespace,
    frame: pd.DataFrame,
    origin: pd.Timestamp | None,
    bounds: tuple[float | None, float | None] | None,
    stdout: TextIO,
) -> int:
    # Metadata and flagged CSVs describe one column; refuse rather than guess.
    if args.unit is not None:
        raise CliError("--unit describes one column; use a single --value-col (or assess_frame in Python)")
    if args.flags_csv:
        raise CliError("--flags-csv needs a single --value-col")
    report = assess_frame(
        frame,
        freq=args.freq,
        bounds=bounds,
        stale_min_run=args.stale_min_run,
        stale_atol=args.stale_atol,
        stale_exclude=args.stale_exclude,
        cumulative=args.cumulative,
        counter_tolerance=args.counter_tolerance,
        jump_max_delta=args.jump_max_delta,
        origin=origin,
        tz=args.tz,
        max_listed=args.max_listed,
    )
    _write_report(args, report, stdout)
    return 1 if args.fail_on_issues and _has_issues(report) else 0


def _load_report(path: str) -> dict[str, object]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CliError(f"file not found: {path}") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise CliError(f"not a JSON report: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise CliError(f"not a JSON report: {path}")
    return data


def _run_compare(args: argparse.Namespace, stdout: TextIO) -> int:
    comparison = compare_reports(_load_report(args.before), _load_report(args.after))
    text = comparison.to_json() + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        stdout.write(text)
    return 1 if args.fail_if_worse and comparison.worse else 0


def main(
    argv: Sequence[str] | None = None,
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Run the CLI and return its exit code (streams are injectable for tests)."""
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    args = build_parser().parse_args(argv)
    try:
        if args.command == "compare":
            return _run_compare(args, stdout)
        return _run_report(args, stdin, stdout)
    except (CliError, ValueError, TypeError) as exc:
        # Library input errors (TimestampError, UnitError, bad freq, ...) are
        # ValueErrors; report them plainly instead of with a traceback.
        print(f"{PROG}: error: {exc}", file=stderr)
        return 2


def console_main() -> None:
    """Entry point for the ``energydata-kit`` console script."""
    sys.exit(main())


if __name__ == "__main__":  # pragma: no cover
    console_main()
