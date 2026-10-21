"""Command-line interface: ``energydata-kit report data.csv ...``.

Reads one timestamp column and one value column from a CSV file (comma-separated
by default; see ``--delimiter`` and ``--decimal``) or a Parquet file (optional
``[parquet]`` extra), runs
:func:`energydata_kit.assess_quality` and prints the deterministic JSON report
(or, with ``--format text`` or ``markdown``, a short summary for reading).
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
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, TextIO

import pandas as pd

from energydata_kit import __version__
from energydata_kit.compare import compare_reports
from energydata_kit.flags import VALUE_COLUMN, QualityFlag, flag_series
from energydata_kit.frame_report import FrameQualityReport, assess_frame, flag_frame
from energydata_kit.intervals import find_missing_intervals, to_step
from energydata_kit.metadata import Aggregation, IntervalLabel, MeasurementMetadata, _grid_from_metadata
from energydata_kit.report import QualityReport, assess_quality
from energydata_kit.table_schema import NAMESPACE, from_table_schema
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


def _rate_option(pair: list[str] | None) -> tuple[float, str] | None:
    # Only DELTA is read here; PERIOD is checked with the other options, with the same messages.
    if pair is None:
        return None
    delta, period = pair
    try:
        return float(delta), period
    except ValueError as exc:
        raise CliError(f"--jump-max-rate DELTA must be a number, got {delta!r}") from exc


def _positive_int(text: str) -> int:
    value = int(text)
    if value < 0:
        raise argparse.ArgumentTypeError("must be >= 0")
    return value


_EXIT_REPORT = "exit status: 0 OK; 1 issues found with --fail-on-issues; 2 usage, input or file error"
_EXIT_COMPARE = "exit status: 0 OK; 1 worse with --fail-if-worse; 2 usage, input or file error"


def build_parser() -> argparse.ArgumentParser:
    """The ``energydata-kit`` argument parser with its ``report`` and ``compare`` subcommands."""
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="Quality checks for energy time-series data.",
        epilog=(
            "exit status: 0 OK; 1 issues found (--fail-on-issues, --fail-if-worse); "
            "2 usage, input or file error"
        ),
    )
    parser.add_argument("--version", action="version", version=f"{PROG} {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    rep = sub.add_parser(
        "report",
        help="print a quality report for a CSV or Parquet file",
        description=(
            "Print a quality report for value columns of a CSV or Parquet file: "
            "deterministic JSON, or a short summary with --format."
        ),
        epilog=_EXIT_REPORT,
    )
    rep.add_argument(
        "csv",
        help="input CSV file, or '-' for standard input; a .parquet, .parq or .pq file is read as "
        "Parquet (needs the [parquet] extra)",
    )

    csv_fmt = rep.add_argument_group("CSV format")
    csv_fmt.add_argument(
        "--delimiter",
        default=",",
        help="field separator: one character, or 'tab' (default: ,)",
    )
    csv_fmt.add_argument(
        "--decimal",
        choices=[".", ","],
        default=".",
        help="decimal mark in values, e.g. ',' with --delimiter ';' (default: .)",
    )

    cols = rep.add_argument_group("columns")
    cols.add_argument("--timestamp-col", default="timestamp", help="timestamp column (default: timestamp)")
    cols.add_argument(
        "--value-col",
        action="append",
        help="value column; repeat for a multi-column report (default: the columns named by --schema "
        "or --unit COLUMN=UNIT, else the only other column)",
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
        "--counter-rollover",
        type=float,
        metavar="M",
        help="the counter's register modulus: drops that wrap past it are rollovers, not decreases",
    )
    checks.add_argument(
        "--jump-max-delta", type=float, help="flag changes larger than this from the previous value"
    )
    checks.add_argument(
        "--jump-max-rate",
        nargs=2,
        metavar=("DELTA", "PERIOD"),
        help="flag changes faster than DELTA per PERIOD since the previous value, e.g. 50 1h",
    )
    checks.add_argument(
        "--max-gap",
        metavar="DURATION",
        help="stale, counter and jump checks skip rows further apart than this, e.g. 1h",
    )

    meta = rep.add_argument_group("measurement metadata (--unit, or --schema)")
    meta.add_argument(
        "--schema",
        help="Table Schema JSON with energydata_kit metadata per column (see to_table_schema); "
        "its columns are the default --value-col",
    )
    meta.add_argument(
        "--unit",
        action="append",
        metavar="[COLUMN=]UNIT",
        help="unit, e.g. kWh for a single column, or COLUMN=UNIT (repeatable) for several; "
        "adds metadata to the report",
    )
    meta.add_argument("--resolution", help="metadata resolution (default: --freq)")
    meta.add_argument("--aggregation", choices=[a.value for a in Aggregation], default="instantaneous")
    meta.add_argument("--interval-label", choices=[lab.value for lab in IntervalLabel], default="start")
    meta.add_argument("--timezone", default=None, help="metadata time zone (default: --tz, else UTC)")

    rep.add_argument(
        "--known-outage",
        nargs=2,
        action="append",
        default=[],
        metavar=("START", "END"),
        help="a period in which data is known to be missing, as timezone-aware ISO 8601 timestamps "
        "(both included); repeatable. Missing intervals inside are counted as explained",
    )
    out = rep.add_argument_group("output")
    out.add_argument("-o", "--output", help="write the report here instead of standard output")
    out.add_argument(
        "--format",
        choices=["json", "text", "markdown"],
        default="json",
        help="json: the deterministic report (default); text: a short summary for reading; "
        "markdown: the same summary as Markdown, e.g. for an issue or pull request",
    )
    out.add_argument(
        "--flags-csv",
        help="also write values and quality flags to this CSV (quality_flag_<col> per column with several)",
    )
    out.add_argument(
        "--gaps-csv",
        help="also write every gap (not only the first --max-listed) to this CSV: "
        "column, start, end, missing_count",
    )
    out.add_argument("--insert-missing", action="store_true", help="add rows for absent grid timestamps")
    out.add_argument("--max-listed", type=_positive_int, default=100, help="cap on listed gaps/duplicates")
    out.add_argument(
        "--fail-on-issues",
        action="store_true",
        help="exit with status 1 if any row is flagged or any interval is missing outside the "
        "--known-outage periods",
    )
    out.add_argument(
        "--fail-on",
        action="append",
        metavar="NAME",
        help="exit with status 1 only for these issues (repeatable): a flag name such as NON_FINITE "
        "or STALE_VALUE, ANY for any flagged row, gaps for any missing interval, or "
        "unexplained-gaps for missing intervals outside the --known-outage periods",
    )

    cmp = sub.add_parser(
        "compare",
        help="print what changed between two saved JSON reports",
        description=(
            "Compare two reports written by 'report': deterministic JSON, or a short summary with --format."
        ),
        epilog=_EXIT_COMPARE,
    )
    cmp.add_argument("before", help="earlier report (JSON)")
    cmp.add_argument("after", help="later report (JSON)")
    cmp.add_argument("-o", "--output", help="write the comparison here instead of standard output")
    cmp.add_argument(
        "--format",
        choices=["json", "text", "markdown"],
        default="json",
        help="json: the deterministic comparison (default); text: a short summary for reading; "
        "markdown: the same summary as Markdown, e.g. for an issue or pull request",
    )
    cmp.add_argument(
        "--fail-if-worse",
        action="store_true",
        help="exit with status 1 if more rows are flagged, more intervals are missing or completeness fell",
    )
    return parser


def _delimiter(args: argparse.Namespace) -> str:
    sep = "\t" if args.delimiter.lower() in {"tab", "\\t"} else args.delimiter
    if len(sep) != 1 or sep in '"\r\n' or sep.isalnum():
        raise CliError(
            f"--delimiter must be one character other than a letter, digit or quote, got {args.delimiter!r}"
        )
    if sep == args.decimal:
        raise CliError(f"--delimiter and --decimal are both {sep!r}")
    return sep


_PARQUET_SUFFIXES = (".parquet", ".parq", ".pq")


def _read_parquet(args: argparse.Namespace) -> pd.DataFrame:
    """Read a Parquet input file (optional [parquet] extra: pyarrow)."""
    if args.delimiter != "," or args.decimal != ".":
        raise CliError("--delimiter and --decimal apply to CSV files only, not Parquet")
    if Path(args.csv).is_dir():  # pandas would read it as a partitioned dataset
        raise CliError(f"{args.csv} is a directory; pass a single Parquet file")
    try:
        frame = pd.read_parquet(args.csv)
    except FileNotFoundError as exc:
        raise CliError(f"file not found: {args.csv}") from exc
    except ImportError as exc:  # pyarrow missing, or installed but unusable (e.g. NumPy too old)
        raise CliError(
            f"reading Parquet needs pyarrow: python -m pip install 'energydata-kit[parquet]' ({exc})"
        ) from exc
    except (OSError, ValueError) as exc:  # pyarrow's errors name a '<Buffer>', not the file
        raise CliError(f"could not read Parquet file {args.csv}: {exc}") from exc
    # pandas writes a named index (often the timestamps) into the file and restores it as
    # the index; make it a column again, as in the CSV of the same data.
    names = list(frame.index.names)
    if all(name is not None for name in names) and not set(names) & set(frame.columns):
        frame = frame.reset_index()
    elif isinstance(frame.index, pd.DatetimeIndex) and args.timestamp_col not in frame.columns:
        raise CliError(
            f"timestamp column {args.timestamp_col!r} not found; the file's timestamps are an unnamed "
            "index: name it (df.index.name = 'timestamp') or make it a column before writing the file"
        )
    return frame


def _read_frame(args: argparse.Namespace, stdin: TextIO) -> pd.DataFrame:
    if args.csv != "-" and args.csv.lower().endswith(_PARQUET_SUFFIXES):
        frame = _read_parquet(args)
        sep = ","  # only used for the CSV hints below
    else:
        sep = _delimiter(args)
        source = stdin if args.csv == "-" else args.csv
        try:
            frame = pd.read_csv(
                source, sep=sep, decimal=args.decimal, dtype={args.timestamp_col: str}, keep_default_na=True
            )
        except FileNotFoundError as exc:
            raise CliError(f"file not found: {args.csv}") from exc
        except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
            raise CliError(f"could not read CSV: {exc}") from exc

    if args.timestamp_col not in frame.columns:
        hint = ""
        found = [s for s in ";\t|," if s != sep and s in str(frame.columns[0])]
        if len(frame.columns) == 1 and found:
            name = "tab" if found[0] == "\t" else found[0]
            hint = f" (the file may be separated by {name!r}; try --delimiter {name!r})"
        raise CliError(
            f"timestamp column {args.timestamp_col!r} not found; columns: {list(frame.columns)}{hint}"
        )
    value_cols = args.value_col
    if value_cols is None and args.schema_metadata:
        value_cols = [c for c in args.schema_metadata if c in frame.columns]
        if not value_cols:
            raise CliError(
                f"none of the --schema columns {list(args.schema_metadata)} are in the file; "
                f"columns: {list(frame.columns)}"
            )
    if value_cols is None and args.unit_by_column:
        # --unit COLUMN=UNIT names the columns, in the order given (P-17).
        value_cols = list(args.unit_by_column)
        missing = [c for c in value_cols if c not in frame.columns]
        if missing:
            raise CliError(
                f"--unit names columns that are not in the file: {missing}; columns: {list(frame.columns)}"
            )
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
        if message.startswith("could not localize"):
            lower = message.lower()
            if "infer dst" in lower or "ambiguous" in lower:
                message += " (repeated wall-clock times at the end of DST: try --ambiguous infer)"
            elif "nonexistent" in lower:
                message += " (wall-clock times skipped at the start of DST: see --nonexistent)"
        raise CliError(message) from exc
    return pd.DataFrame({str(c): frame[c].to_numpy() for c in value_cols}, index=index)


def _load_schema(path: str) -> dict[str, MeasurementMetadata]:
    """Metadata per column from a Table Schema file, in field order."""
    try:
        schema = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CliError(f"file not found: {path}") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise CliError(f"not a JSON Table Schema: {path}: {exc}") from exc
    if not isinstance(schema, dict) or not isinstance(schema.get("fields"), list):
        raise CliError(f"not a JSON Table Schema (no 'fields' list): {path}")
    names = [f["name"] for f in schema["fields"] if isinstance(f, dict) and NAMESPACE in f and "name" in f]
    if not names:
        raise CliError(f"no fields with {NAMESPACE!r} metadata in {path}")
    try:
        return {name: from_table_schema(schema, field=name) for name in names}
    except (ValueError, KeyError, TypeError) as exc:
        raise CliError(f"invalid metadata in {path}: {exc}") from exc


def _units(given: list[str] | None) -> tuple[str | None, dict[str, str]]:
    """``--unit`` values as one unit for a single column, or units per column (``COLUMN=UNIT``)."""
    if not given:
        return None, {}
    plain = [u for u in given if "=" not in u]
    if plain and len(given) > 1:
        raise CliError("--unit UNIT describes a single column; for several, repeat --unit COLUMN=UNIT")
    if plain:
        return plain[0], {}
    by_column: dict[str, str] = {}
    for item in given:
        column, unit = item.rsplit("=", 1)  # units never contain "="; column names might
        if not column or not unit:
            raise CliError(f"--unit {item!r}: expected COLUMN=UNIT")
        if column in by_column:
            raise CliError(f"--unit names column {column!r} twice")
        by_column[column] = unit
    return None, by_column


def _metadata(args: argparse.Namespace, name: str) -> MeasurementMetadata | None:
    schema_metadata: dict[str, MeasurementMetadata] = args.schema_metadata
    if name in schema_metadata:
        return schema_metadata[name]
    unit = args.unit_for_all or args.unit_by_column.get(name)
    if unit is None:
        return None
    return MeasurementMetadata(
        name=name,
        unit=unit,
        resolution=args.resolution or args.freq,
        aggregation=Aggregation(args.aggregation),
        interval_label=IntervalLabel(args.interval_label),
        timezone=args.timezone or args.tz or "UTC",
    )


_GAP_ISSUES = ("gaps", "unexplained-gaps")


def _fail_on(names: list[str] | None) -> list[str] | None:
    """--fail-on names, checked and normalised: flag names in upper case, gap names in lower case."""
    if names is None:
        return None
    known = [m.name for m in QualityFlag if m.name and m.value and m is not QualityFlag.MISSING_INTERVAL]
    known.append("ANY")
    checked = []
    for name in names:
        if name.lower() in _GAP_ISSUES:
            checked.append(name.lower())
        elif name.upper() in known:
            checked.append(name.upper())
        else:
            raise CliError(f"--fail-on {name!r} is not an issue name; use one of {[*known, *_GAP_ISSUES]}")
    return checked


def _issue_found(r: QualityReport, name: str) -> bool:
    unexplained = r.n_missing_intervals - (r.n_missing_explained or 0)
    if name == "gaps":
        return r.n_missing_intervals > 0
    if name == "unexplained-gaps":
        return unexplained > 0
    return r.flag_counts.get(name, 0) > 0


def _exit_status(args: argparse.Namespace, report: QualityReport | FrameQualityReport) -> int:
    """1 when an issue that should fail the command was found, else 0.

    --fail-on-issues: any flagged row or any missing interval outside the --known-outage periods
    (P-21). --fail-on NAME: only the named issues (P-23).
    """
    names = ["ANY", "unexplained-gaps"] if args.fail_on_issues else args.fail_on or []
    reports = report.columns.values() if isinstance(report, FrameQualityReport) else [report]
    return int(any(_issue_found(r, name) for r in reports for name in names))


def _write_flags(args: argparse.Namespace, flagged: pd.DataFrame) -> None:
    """Write the flagged table in the input's CSV format (delimiter and decimal mark).

    Lines end in ``\n`` on every platform, so the file is the same on Windows.
    """
    flagged.to_csv(
        args.flags_csv,
        sep=_delimiter(args),
        decimal=args.decimal,
        date_format="%Y-%m-%dT%H:%M:%S%z",
        lineterminator="\n",
    )


def _gap_grids(
    args: argparse.Namespace, metadata: Mapping[str, MeasurementMetadata | None], columns: list[str]
) -> dict[str, tuple[str | pd.Timedelta, str | None]]:
    """The grid each column's report uses, for --gaps-csv; refused before anything is written."""
    grids: dict[str, tuple[str | pd.Timedelta, str | None]] = {}
    no_step = []
    for column in columns:
        freq, tz = _grid_from_metadata(args.freq, args.tz, metadata.get(column))
        if freq is None:
            no_step.append(column)
        else:
            grids[column] = (freq, tz)
    if no_step:
        raise CliError(
            f"--gaps-csv needs a step for every column; {no_step} have none: pass --freq or a resolution"
        )
    return grids


def _write_gaps(
    args: argparse.Namespace,
    index: pd.Index,
    grids: dict[str, tuple[str | pd.Timedelta, str | None]],
    origin: pd.Timestamp | None,
) -> None:
    """Every gap per column, on the column's report grid, in the input's CSV format.

    Lines end in ``\n`` on every platform, as in :func:`_write_flags`.
    """
    assert isinstance(index, pd.DatetimeIndex)  # _read_frame normalizes the timestamps
    rows = [
        (column, gap.start, gap.end, gap.missing_count)
        for column, (freq, tz) in grids.items()
        for gap in (find_missing_intervals(index, freq, origin=origin, tz=tz) if len(index) else [])
    ]
    table = pd.DataFrame(rows, columns=["column", "start", "end", "missing_count"])
    for name in ("start", "end"):
        table[name] = pd.to_datetime(table[name], utc=True)
    table.to_csv(
        args.gaps_csv,
        sep=_delimiter(args),
        index=False,
        date_format="%Y-%m-%dT%H:%M:%S%z",
        lineterminator="\n",
    )


def _run_report(args: argparse.Namespace, stdin: TextIO, stdout: TextIO) -> int:
    if args.tz and not args.freq:
        raise CliError("--tz needs --freq")
    if args.insert_missing and not args.flags_csv:
        raise CliError("--insert-missing only affects --flags-csv")
    if args.schema and args.unit is not None:
        raise CliError("--schema and --unit both set metadata; use one")
    if args.fail_on_issues and args.fail_on:
        raise CliError("--fail-on-issues and --fail-on both choose what fails; use one")
    args.fail_on = _fail_on(args.fail_on)
    if args.unit is None and (
        args.resolution
        or args.timezone
        or args.aggregation != "instantaneous"
        or args.interval_label != "start"
    ):
        raise CliError(
            "--resolution, --aggregation, --interval-label and --timezone describe the metadata set "
            "with --unit; pass --unit too (for the grid step alone, use --freq)"
        )
    args.schema_metadata = _load_schema(args.schema) if args.schema else {}
    args.unit_for_all, args.unit_by_column = _units(args.unit)
    args.jump_max_rate = _rate_option(args.jump_max_rate)

    frame = _read_frame(args, stdin)
    unknown = [c for c in args.unit_by_column if c not in frame.columns]
    if unknown:
        raise CliError(
            f"--unit names columns that are not assessed: {unknown}; columns: {list(frame.columns)}"
        )
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
        counter_rollover=args.counter_rollover,
        jump_max_delta=args.jump_max_delta,
        jump_max_rate=args.jump_max_rate,
        max_gap=args.max_gap,
        origin=origin,
        tz=args.tz,
        known_outages=args.known_outage,
        max_listed=args.max_listed,
    )
    gap_grids = _gap_grids(args, {str(series.name): metadata}, [str(series.name)]) if args.gaps_csv else {}
    _write_report(args, report, stdout)
    if args.gaps_csv:
        _write_gaps(args, series.index, gap_grids, origin)

    if args.flags_csv:
        freq, tz = _grid_from_metadata(args.freq, args.tz, metadata)  # the report's grid
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
            counter_rollover=args.counter_rollover,
            jump_max_delta=args.jump_max_delta,
            jump_max_rate=args.jump_max_rate,
            max_gap=args.max_gap,
            origin=origin,
            tz=tz,
        )
        flagged = flagged.rename(columns={VALUE_COLUMN: series.name})
        flagged.index.name = args.timestamp_col
        _write_flags(args, flagged)

    return _exit_status(args, report)


def _write_report(
    args: argparse.Namespace, report: QualityReport | FrameQualityReport, stdout: TextIO
) -> None:
    if args.format == "json":
        text = report.to_json() + "\n"
    else:
        text = _summary(report.to_dict(), markdown=args.format == "markdown")
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8", newline="\n")  # same bytes on Windows
    else:
        stdout.write(text)


_Facts = list[tuple[str | None, str]]  # (label or None, text), shared by --format text and markdown


def _series_facts(data: dict[str, Any]) -> tuple[str, _Facts]:
    """Headline and labelled facts for one single-series report dict."""
    head = f"{data['n_rows']} rows"
    if data["n_rows"]:
        head += f", {data['first_timestamp']} to {data['last_timestamp']}"
    facts: _Facts = []
    if data["completeness"] is None:
        if not data["n_rows"]:
            why = "not checked (no rows)"
        elif data["n_expected_intervals"] is None:
            why = "not checked (no step: pass --freq, or a resolution with --unit or --schema)"
        else:
            why = "undefined (no expected interval within the data's time span)"
        facts.append(("completeness", why))
    else:
        # Exact; rebuilding it from the rounded completeness is off by one or more above ~10**6 intervals.
        present = data["n_expected_intervals"] - data["n_missing_intervals"]
        facts.append(
            (
                "completeness",
                f"{data['completeness']:.2%} ({present} of {data['n_expected_intervals']} expected); "
                f"{data['n_missing_intervals']} missing in {data['n_gaps']} gap(s)",
            )
        )
    flags = {k: v for k, v in data["flag_counts"].items() if v and k != "ANY"}
    detail = ", ".join(f"{k} {v}" for k, v in flags.items())
    facts.append(("flagged rows", f"{data['flag_counts']['ANY']}" + (f" ({detail})" if detail else "")))
    if data["n_duplicate_timestamps"]:
        facts.append(("duplicate timestamps", str(data["n_duplicate_timestamps"])))
    gaps = data["gaps"]
    shown = gaps[:3]
    for gap in shown:
        facts.append(("gap", f"{gap['start']} to {gap['end']} ({gap['missing_count']} missing)"))
    if data["n_gaps"] > len(shown):  # also when --max-listed listed fewer than three
        facts.append((None, f"... {data['n_gaps'] - len(shown)} more gap(s); see the JSON report"))
    if data["parameters"].get("known_outages"):
        rest = data["completeness_excluding_outages"]
        facts.append(
            (
                "known outages",
                f"{len(data['parameters']['known_outages'])} period(s); "
                f"{data['n_missing_explained']} of the missing intervals inside; completeness without them "
                + ("not defined" if rest is None else f"{rest:.2%}"),
            )
        )
    if data["metadata_issues"]:
        facts.append(("metadata issues", ", ".join(issue["code"] for issue in data["metadata_issues"])))
    return head, facts


_MARKDOWN_SPECIAL = re.compile(r"([\\`*_\[\]<>#|&~$])")
_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f\u2028\u2029]+")


def _one_line(text: str) -> str:
    """User-supplied text (column names) with line breaks and other control characters as one space."""
    return _CONTROL.sub(" ", text)


def _md(text: str) -> str:
    """Escape user-supplied text (column names) for Markdown, on one line."""
    return _MARKDOWN_SPECIAL.sub(r"\\\1", _one_line(text))


def _md_facts(facts: _Facts) -> list[str]:
    return [f"- **{label}:** {text}" if label else f"- {text}" for label, text in facts]


def _summary(data: dict[str, Any], markdown: bool = False) -> str:
    """A short human-readable summary of a report dict (``--format text`` or ``markdown``)."""
    single = "columns" not in data
    series = (
        [(data["series_name"] or "series", data)]
        if single
        else [(name, data["columns"][name]) for name in data["column_order"]]
    )
    footer = f"{data['fingerprint'][:16]} (energydata-kit {data['package_version']})"
    if markdown:
        title = _md(series[0][0]) if single else f"{len(series)} column(s)"
        lines = [f"# Quality report: {title}"]
        for name, part in series:
            head, facts = _series_facts(part)
            lines += [""] + ([] if single else [f"## {_md(name)}", ""]) + [head, ""] + _md_facts(facts)
        lines += ["", f"Fingerprint `{data['fingerprint'][:16]}` (energydata-kit {data['package_version']})"]
        return "\n".join(lines) + "\n"
    indent = "" if single else "  "
    lines = [] if single else [f"{len(series)} column(s)"]
    for name, part in series:
        head, facts = _series_facts(part)
        lines.append(f"{indent}{_one_line(name)}: {head}")
        lines += [f"{indent}  {label}: {text}" if label else f"{indent}  {text}" for label, text in facts]
    lines.append(f"fingerprint: {footer}")
    return "\n".join(lines) + "\n"


def _run_frame_report(
    args: argparse.Namespace,
    frame: pd.DataFrame,
    origin: pd.Timestamp | None,
    bounds: tuple[float | None, float | None] | None,
    stdout: TextIO,
) -> int:
    # A plain --unit describes one column; refuse rather than guess. --schema and
    # --unit COLUMN=UNIT name their columns.
    if args.unit_for_all is not None:
        raise CliError(
            "--unit UNIT describes a single column; for several, repeat --unit COLUMN=UNIT, or use --schema"
        )
    named = {str(c): _metadata(args, str(c)) for c in frame.columns}
    metadata = {c: m for c, m in named.items() if m is not None}
    checks: dict[str, Any] = {
        "bounds": bounds,
        "stale_min_run": args.stale_min_run,
        "stale_atol": args.stale_atol,
        "stale_exclude": args.stale_exclude,
        "cumulative": args.cumulative,
        "counter_tolerance": args.counter_tolerance,
        "counter_rollover": args.counter_rollover,
        "jump_max_delta": args.jump_max_delta,
        "jump_max_rate": args.jump_max_rate,
        "max_gap": args.max_gap,
    }
    report = assess_frame(
        frame,
        metadata=metadata,
        freq=args.freq,
        origin=origin,
        tz=args.tz,
        known_outages=args.known_outage,
        max_listed=args.max_listed,
        **checks,
    )
    freq, tz = args.freq, args.tz
    if args.flags_csv and freq is None:
        # As in the report, the metadata resolution is the step (in the metadata's time zone for
        # calendar steps); one table needs one grid. Checked before anything is written, so a
        # failed command leaves no report behind.
        grids: dict[tuple[object, str | None], tuple[str | pd.Timedelta | None, str | None]] = {}
        for m in metadata.values():
            if m.resolution is not None:
                step, zone = _grid_from_metadata(None, None, m)
                # Steps compare by value, so "60min" and "1h" (or "MS" and "1MS") are one grid.
                assert step is not None  # m.resolution is set
                key = (to_step(step) if zone is None else pd.tseries.frequencies.to_offset(step), zone)
                grids.setdefault(key, (step, zone))
        if len(grids) > 1:
            steps = sorted({f"{f} ({z})" if z else str(f) for f, z in grids.values()})
            raise CliError(f"--schema columns have different resolutions {steps}; pass --freq")
        no_step = [c for c in frame.columns if c not in metadata or metadata[c].resolution is None]
        if grids and no_step:
            # Their reports have no grid; flagging them on another column's grid would disagree.
            raise CliError(
                f"columns {no_step} have no resolution in --schema while others do; "
                "give each column a resolution, or pass --freq"
            )
        freq, tz = next(iter(grids.values()), (None, None))
    gap_grids = _gap_grids(args, metadata, [str(c) for c in frame.columns]) if args.gaps_csv else {}
    _write_report(args, report, stdout)
    if args.gaps_csv:
        _write_gaps(args, frame.index, gap_grids, origin)
    if args.flags_csv:
        flagged = flag_frame(
            frame, freq=freq, insert_missing=args.insert_missing, origin=origin, tz=tz, **checks
        )
        flagged.index.name = args.timestamp_col
        _write_flags(args, flagged)
    return _exit_status(args, report)


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


def _change(label: str, entry: dict[str, Any], percent: bool = False) -> str:
    def fmt(value: Any) -> str:
        if value is None:
            return "none"
        return f"{value:.2%}" if percent else str(value)

    text = f"{label} {fmt(entry['before'])} -> {fmt(entry['after'])}"
    if not percent and isinstance(entry.get("delta"), int):
        text += f" ({entry['delta']:+d})"
    return text


def _changes_facts(changes: dict[str, Any]) -> list[str]:
    """One line per kind of change for one series of a comparison dict."""
    counts_order = (
        ("n_rows", "rows"),
        ("n_missing_intervals", "missing intervals"),
        ("n_missing_explained", "missing in known outages"),
        ("n_gaps", "gaps"),
        ("n_duplicate_timestamps", "duplicate timestamps"),
    )
    lines = []
    counts = changes.get("counts", {})
    parts = [_change(text, counts[key]) for key, text in counts_order if key in counts]
    if "completeness" in counts:
        parts.append(_change("completeness", counts["completeness"], percent=True))
    if "completeness_excluding_outages" in counts:
        parts.append(
            _change(
                "completeness without known outages", counts["completeness_excluding_outages"], percent=True
            )
        )
    if parts:
        lines.append("; ".join(parts))
    flags = changes.get("flag_counts", {})
    if flags:
        detail = ", ".join(_change(k, v) for k, v in flags.items() if k != "ANY")
        head = _change("flagged rows", flags["ANY"]) if "ANY" in flags else "flags"
        lines.append(head + (f": {detail}" if detail else ""))
    if "gaps" in changes:
        gaps = changes["gaps"]
        note = " (lists truncated; see the JSON reports)" if gaps["lists_truncated"] else ""
        counts_text = f"resolved: {len(gaps['resolved'])}, new: {len(gaps['new'])}"
        lines.append(f"gaps {counts_text}, changed: {len(gaps['changed'])}{note}")
    if "metadata_issues" in changes:
        issues = changes["metadata_issues"]
        resolved, new = ", ".join(issues["resolved"]) or "none", ", ".join(issues["new"]) or "none"
        lines.append(f"metadata issues resolved: {resolved}; new: {new}")
    for key in ("parameters", "metadata"):
        if key in changes:
            lines.append(f"{key} changed: {', '.join(changes[key])}")
    return lines


def _comparison_summary(data: dict[str, Any], markdown: bool = False) -> str:
    """A short human-readable summary of a comparison dict (``compare --format text`` or ``markdown``)."""
    verdict = "same data" if data["same_data"] else "data changed"
    if data["worse"]:
        verdict += "; worse: more rows flagged, more intervals missing or lower completeness"
    else:
        verdict += "; not worse"
    added, removed = ", ".join(data["columns_added"]), ", ".join(data["columns_removed"])
    if markdown:
        lines = ["# Report comparison", "", f"**{verdict}**"]
        for name, changes in data["changes"].items():
            lines += ["", f"## {_md(name or 'series')}", ""]
            facts = _changes_facts(changes)
            lines += [f"- {line}" for line in facts] if facts else ["No changes."]
        if added:
            lines += ["", f"Columns added: {_md(added)}"]
        if removed:
            lines += ["", f"Columns removed: {_md(removed)}"]
        return "\n".join(lines) + "\n"
    lines = [verdict]
    for name, changes in data["changes"].items():
        label = _one_line(name) or "series"
        if not changes:
            lines.append(f"{label}: no changes")
            continue
        lines.append(f"{label}:")
        lines += [f"  {line}" for line in _changes_facts(changes)]
    if added:
        lines.append(f"columns added: {_one_line(added)}")
    if removed:
        lines.append(f"columns removed: {_one_line(removed)}")
    return "\n".join(lines) + "\n"


def _run_compare(args: argparse.Namespace, stdout: TextIO) -> int:
    comparison = compare_reports(_load_report(args.before), _load_report(args.after))
    if args.format == "json":
        text = comparison.to_json() + "\n"
    else:
        text = _comparison_summary(comparison.to_dict(), markdown=args.format == "markdown")
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8", newline="\n")  # same bytes on Windows
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
    except OSError as exc:
        # Unreadable inputs or unwritable outputs (a directory, a missing parent
        # directory, no permission). Exit 2, not a traceback: Python's own exit
        # status 1 would read as "issues found".
        where = f": {exc.filename}" if exc.filename else ""
        print(f"{PROG}: error: {exc.strerror or exc}{where}", file=stderr)
        return 2


def console_main() -> None:
    """Entry point for the ``energydata-kit`` console script."""
    sys.exit(main())


if __name__ == "__main__":  # pragma: no cover
    console_main()
