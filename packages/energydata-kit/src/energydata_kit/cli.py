"""Command-line interface: ``energydata-kit report data.csv ...``.

Reads one timestamp column and one value column from a CSV file (comma-separated
by default; see ``--delimiter`` and ``--decimal``), runs
:func:`energydata_kit.assess_quality` and prints the deterministic JSON report
(or, with ``--format text``, a short summary for reading).
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
from typing import Any, TextIO

import pandas as pd

from energydata_kit import __version__
from energydata_kit.compare import compare_reports
from energydata_kit.flags import VALUE_COLUMN, flag_series
from energydata_kit.frame_report import FrameQualityReport, assess_frame, flag_frame
from energydata_kit.metadata import Aggregation, IntervalLabel, MeasurementMetadata
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


def _positive_int(text: str) -> int:
    value = int(text)
    if value < 0:
        raise argparse.ArgumentTypeError("must be >= 0")
    return value


def build_parser() -> argparse.ArgumentParser:
    """The ``energydata-kit`` argument parser with its ``report`` and ``compare`` subcommands."""
    parser = argparse.ArgumentParser(prog=PROG, description="Quality checks for energy time-series data.")
    parser.add_argument("--version", action="version", version=f"{PROG} {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    rep = sub.add_parser(
        "report",
        help="print a JSON quality report for a CSV file",
        description="Print a deterministic JSON quality report for value columns of a CSV file.",
    )
    rep.add_argument("csv", help="input CSV file, or '-' for standard input")

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

    meta = rep.add_argument_group("measurement metadata (--unit for one column, or --schema)")
    meta.add_argument(
        "--schema",
        help="Table Schema JSON with energydata_kit metadata per column (see to_table_schema); "
        "its columns are the default --value-col",
    )
    meta.add_argument("--unit", help="unit, e.g. kW or kWh; adds metadata to the report")
    meta.add_argument("--resolution", help="metadata resolution (default: --freq)")
    meta.add_argument("--aggregation", choices=[a.value for a in Aggregation], default="instantaneous")
    meta.add_argument("--interval-label", choices=[lab.value for lab in IntervalLabel], default="start")
    meta.add_argument("--timezone", default=None, help="metadata time zone (default: --tz, else UTC)")

    out = rep.add_argument_group("output")
    out.add_argument("-o", "--output", help="write the report here instead of standard output")
    out.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="json: the deterministic report (default); text: a short summary for reading",
    )
    out.add_argument(
        "--flags-csv",
        help="also write values and quality flags to this CSV (quality_flag_<col> per column with several)",
    )
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
        "--format",
        choices=["json", "text"],
        default="json",
        help="json: the deterministic comparison (default); text: a short summary for reading",
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


def _read_frame(args: argparse.Namespace, stdin: TextIO) -> pd.DataFrame:
    source = stdin if args.csv == "-" else args.csv
    sep = _delimiter(args)
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


def _metadata(args: argparse.Namespace, name: str) -> MeasurementMetadata | None:
    schema_metadata: dict[str, MeasurementMetadata] = args.schema_metadata
    if name in schema_metadata:
        return schema_metadata[name]
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


def _write_flags(args: argparse.Namespace, flagged: pd.DataFrame) -> None:
    """Write the flagged table in the input's CSV format (delimiter and decimal mark)."""
    flagged.to_csv(
        args.flags_csv, sep=_delimiter(args), decimal=args.decimal, date_format="%Y-%m-%dT%H:%M:%S%z"
    )


def _run_report(args: argparse.Namespace, stdin: TextIO, stdout: TextIO) -> int:
    if args.tz and not args.freq:
        raise CliError("--tz needs --freq")
    if args.insert_missing and not args.flags_csv:
        raise CliError("--insert-missing only affects --flags-csv")
    if args.schema and args.unit is not None:
        raise CliError("--schema and --unit both set metadata; use one")
    args.schema_metadata = _load_schema(args.schema) if args.schema else {}

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
        _write_flags(args, flagged)

    return 1 if args.fail_on_issues and _has_issues(report) else 0


def _write_report(
    args: argparse.Namespace, report: QualityReport | FrameQualityReport, stdout: TextIO
) -> None:
    text = report.to_json() + "\n" if args.format == "json" else _summary(report.to_dict())
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        stdout.write(text)


def _series_summary(name: str, data: dict[str, Any], indent: str = "") -> list[str]:
    """Summary lines for one single-series report dict."""
    lines = [f"{indent}{name}: {data['n_rows']} rows"]
    if data["n_rows"]:
        lines[0] += f", {data['first_timestamp']} to {data['last_timestamp']}"
    pad = indent + "  "
    if data["completeness"] is None:
        lines.append(f"{pad}completeness: not checked (no --freq or --resolution)")
    else:
        present = round(data["completeness"] * data["n_expected_intervals"])
        lines.append(
            f"{pad}completeness: {data['completeness']:.2%} ({present} of {data['n_expected_intervals']} "
            f"expected); {data['n_missing_intervals']} missing in {data['n_gaps']} gap(s)"
        )
    flags = {k: v for k, v in data["flag_counts"].items() if v and k != "ANY"}
    detail = ", ".join(f"{k} {v}" for k, v in flags.items())
    lines.append(f"{pad}flagged rows: {data['flag_counts']['ANY']}" + (f" ({detail})" if detail else ""))
    if data["n_duplicate_timestamps"]:
        lines.append(f"{pad}duplicate timestamps: {data['n_duplicate_timestamps']}")
    gaps = data["gaps"]
    shown = gaps[:3]
    for gap in shown:
        lines.append(f"{pad}gap: {gap['start']} to {gap['end']} ({gap['missing_count']} missing)")
    if data["n_gaps"] > len(shown):  # also when --max-listed listed fewer than three
        lines.append(f"{pad}... {data['n_gaps'] - len(shown)} more gap(s); see the JSON report")
    if data["metadata_issues"]:
        codes = ", ".join(issue["code"] for issue in data["metadata_issues"])
        lines.append(f"{pad}metadata issues: {codes}")
    return lines


def _summary(data: dict[str, Any]) -> str:
    """A short human-readable summary of a report dict (``--format text``)."""
    if "columns" not in data:
        lines = _series_summary(data["series_name"] or "series", data)
    else:
        lines = [f"{len(data['column_order'])} column(s)"]
        for name in data["column_order"]:
            lines += _series_summary(name, data["columns"][name], indent="  ")
    lines.append(f"fingerprint: {data['fingerprint'][:16]} (energydata-kit {data['package_version']})")
    return "\n".join(lines) + "\n"


def _run_frame_report(
    args: argparse.Namespace,
    frame: pd.DataFrame,
    origin: pd.Timestamp | None,
    bounds: tuple[float | None, float | None] | None,
    stdout: TextIO,
) -> int:
    # --unit describes one column; refuse rather than guess. --schema names its columns.
    if args.unit is not None:
        raise CliError("--unit describes one column; use a single --value-col, or --schema")
    metadata = {c: m for c, m in args.schema_metadata.items() if c in frame.columns}
    checks: dict[str, Any] = {
        "bounds": bounds,
        "stale_min_run": args.stale_min_run,
        "stale_atol": args.stale_atol,
        "stale_exclude": args.stale_exclude,
        "cumulative": args.cumulative,
        "counter_tolerance": args.counter_tolerance,
        "jump_max_delta": args.jump_max_delta,
    }
    report = assess_frame(
        frame,
        metadata=metadata,
        freq=args.freq,
        origin=origin,
        tz=args.tz,
        max_listed=args.max_listed,
        **checks,
    )
    _write_report(args, report, stdout)
    if args.flags_csv:
        freq = args.freq
        if freq is None:
            # As in the report, the metadata resolution is the step; one table needs one step.
            steps = {str(m.resolution) for m in metadata.values() if m.resolution is not None}
            if len(steps) > 1:
                raise CliError(f"--schema columns have different resolutions {sorted(steps)}; pass --freq")
            freq = next((m.resolution for m in metadata.values() if m.resolution is not None), None)
        flagged = flag_frame(
            frame, freq=freq, insert_missing=args.insert_missing, origin=origin, tz=args.tz, **checks
        )
        flagged.index.name = args.timestamp_col
        _write_flags(args, flagged)
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


def _change(label: str, entry: dict[str, Any], percent: bool = False) -> str:
    def fmt(value: Any) -> str:
        if value is None:
            return "none"
        return f"{value:.2%}" if percent else str(value)

    text = f"{label} {fmt(entry['before'])} -> {fmt(entry['after'])}"
    if not percent and isinstance(entry.get("delta"), int):
        text += f" ({entry['delta']:+d})"
    return text


def _comparison_summary(data: dict[str, Any]) -> str:
    """A short human-readable summary of a comparison dict (``compare --format text``)."""
    verdict = "same data" if data["same_data"] else "data changed"
    if data["worse"]:
        verdict += "; worse: more rows flagged, more intervals missing or lower completeness"
    else:
        verdict += "; not worse"
    lines = [verdict]
    counts_order = (
        ("n_rows", "rows"),
        ("n_missing_intervals", "missing intervals"),
        ("n_gaps", "gaps"),
        ("n_duplicate_timestamps", "duplicate timestamps"),
    )
    for name, changes in data["changes"].items():
        label = name or "series"
        if not changes:
            lines.append(f"{label}: no changes")
            continue
        lines.append(f"{label}:")
        counts = changes.get("counts", {})
        parts = [_change(text, counts[key]) for key, text in counts_order if key in counts]
        if "completeness" in counts:
            parts.append(_change("completeness", counts["completeness"], percent=True))
        if parts:
            lines.append("  " + "; ".join(parts))
        flags = changes.get("flag_counts", {})
        if flags:
            detail = ", ".join(_change(k, v) for k, v in flags.items() if k != "ANY")
            head = _change("flagged rows", flags["ANY"]) if "ANY" in flags else "flags"
            lines.append(f"  {head}" + (f": {detail}" if detail else ""))
        if "gaps" in changes:
            gaps = changes["gaps"]
            note = " (lists truncated; see the JSON reports)" if gaps["lists_truncated"] else ""
            lines.append(f"  gaps resolved: {len(gaps['resolved'])}, new: {len(gaps['new'])}{note}")
        if "metadata_issues" in changes:
            issues = changes["metadata_issues"]
            resolved, new = ", ".join(issues["resolved"]) or "none", ", ".join(issues["new"]) or "none"
            lines.append(f"  metadata issues resolved: {resolved}; new: {new}")
        for key in ("parameters", "metadata"):
            if key in changes:
                lines.append(f"  {key} changed: {', '.join(changes[key])}")
    if data["columns_added"]:
        lines.append(f"columns added: {', '.join(data['columns_added'])}")
    if data["columns_removed"]:
        lines.append(f"columns removed: {', '.join(data['columns_removed'])}")
    return "\n".join(lines) + "\n"


def _run_compare(args: argparse.Namespace, stdout: TextIO) -> int:
    comparison = compare_reports(_load_report(args.before), _load_report(args.after))
    text = comparison.to_json() + "\n" if args.format == "json" else _comparison_summary(comparison.to_dict())
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
