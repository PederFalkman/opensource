"""Command-line interface: ``energydata-kit report data.csv ...``.

Reads one timestamp column and one value column from a CSV file, runs
:func:`energydata_kit.assess_quality` and prints the deterministic JSON report.
Optionally writes the non-destructive flagged table from
:func:`energydata_kit.flag_series`.

Exit codes: 0 success; 1 ``--fail-on-issues`` and issues were found;
2 usage, input or data error.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

import pandas as pd

from energydata_kit import __version__
from energydata_kit.flags import VALUE_COLUMN, flag_series
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
        description="Print a deterministic JSON quality report for one value column of a CSV file.",
    )
    rep.add_argument("csv", help="input CSV file, or '-' for standard input")

    cols = rep.add_argument_group("columns")
    cols.add_argument("--timestamp-col", default="timestamp", help="timestamp column (default: timestamp)")
    cols.add_argument(
        "--value-col", help="value column (default: the only other column; required if there are several)"
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
    return parser


def _read_series(args: argparse.Namespace, stdin: TextIO) -> pd.Series:
    source = stdin if args.csv == "-" else args.csv
    try:
        frame = pd.read_csv(source, dtype={args.timestamp_col: str}, keep_default_na=True)
    except FileNotFoundError as exc:
        raise CliError(f"file not found: {args.csv}") from exc
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
        raise CliError(f"could not read CSV: {exc}") from exc

    if args.timestamp_col not in frame.columns:
        raise CliError(f"timestamp column {args.timestamp_col!r} not found; columns: {list(frame.columns)}")
    value_col = args.value_col
    if value_col is None:
        others = [c for c in frame.columns if c != args.timestamp_col]
        if len(others) != 1:
            raise CliError(f"pass --value-col; candidate columns: {others}")
        value_col = others[0]
    elif value_col not in frame.columns:
        raise CliError(f"value column {value_col!r} not found; columns: {list(frame.columns)}")

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
    return pd.Series(frame[value_col].to_numpy(), index=index, name=str(value_col))


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


def _has_issues(report: QualityReport) -> bool:
    return report.n_flagged_rows > 0 or report.n_missing_intervals > 0


def _run_report(args: argparse.Namespace, stdin: TextIO, stdout: TextIO) -> int:
    if args.tz and not args.freq:
        raise CliError("--tz needs --freq")
    if args.insert_missing and not args.flags_csv:
        raise CliError("--insert-missing only affects --flags-csv")

    series = _read_series(args, stdin)
    metadata = _metadata(args, str(series.name))
    origin = None if args.origin is None else pd.Timestamp(args.origin)
    bounds = None if args.bounds is None else (args.bounds[0], args.bounds[1])

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
    text = report.to_json() + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        stdout.write(text)

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
