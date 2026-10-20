# energydata-kit

Framework-independent quality checks for energy time-series data.

> **Status: 0.2.0, released as a GitHub release** (wheel and sdist attached
> to the tag `energydata-kit-v0.2.0`); not published to PyPI or any other
> index. Licensed Apache-2.0 (`LICENSE`). This branch is 0.3.0
> development; changes since 0.2.0 are under `[Unreleased]` in the changelog.

energydata-kit is a small layer on top of [pandas](https://pandas.pydata.org)
and [Pint](https://pint.readthedocs.io). It adds the parts those libraries do not
cover for metered energy data:

| Capability | Function(s) |
|---|---|
| Normalize timestamps to tz-aware UTC, with explicit DST policies | `normalize_timestamps` |
| Describe an index (monotonic, unique, inferred step) | `summarize_timestamps`, `infer_resolution` |
| Missing intervals on a fixed UTC grid or a local-calendar grid (`tz=`), with an optional `origin` | `find_missing_intervals`, `missing_timestamps`, `expected_grid` |
| Duplicate and off-grid timestamps | `find_duplicate_timestamps`, `duplicate_mask`, `off_grid_mask` |
| Missing, non-finite, non-numeric and out-of-bounds values | `missing_value_mask`, `non_finite_mask`, `non_numeric_mask`, `out_of_bounds_mask` |
| Stale (flat-line) values, cumulative-counter decreases and jumps between consecutive values, as an absolute limit or a rate per unit of time (opt-in) | `stale_mask`, `counter_decrease_mask`, `counter_rollover_mask`, `jump_mask`, `jump_rate_mask` |
| Non-destructive bitmask quality flags | `flag_series`, `QualityFlag`, `decode_flags` |
| Unit and measurement metadata (units parsed by Pint) | `MeasurementMetadata`, `validate_unit`, `units_compatible` |
| Explicit start/end interval relabelling | `relabel_intervals`, `interval_bounds` |
| Unit / aggregation consistency advice | `check_metadata_consistency`, `MetadataIssue` |
| Completeness per local calendar day (DST-aware: 92/96/100 at 15 min) | `local_day_completeness` |
| Known outage periods: missing intervals inside them counted as explained | `assess_quality(..., known_outages=...)`, `--known-outage` |
| Reproducible JSON quality reports, with a JSON Schema for the format | `assess_quality`, `QualityReport`, `fingerprint_series`, `report_schema.json` |
| One report for several columns sharing a timestamp index, with per-column options and the shared timestamp facts stated once | `assess_frame`, `FrameQualityReport` |
| Flags for several columns at once (`quality_flag_<column>` each) | `flag_frame`, `flag_column` |
| What changed between two reports (e.g. before and after a fix, or two deliveries) | `compare_reports`, `ReportComparison` |
| Deterministic synthetic test series | `make_synthetic_series` |
| Command line: JSON report for one or more CSV or Parquet columns, flagged CSV, report comparison | `energydata-kit report`, `energydata-kit compare` |
| Supporting types and constants | `Aggregation`, `IntervalLabel`, `TimestampSummary`, `FLAG_COLUMN` / `VALUE_COLUMN` (column names in `flag_series` output); errors `TimestampError`, `UnitError` (both `ValueError`s) |
| Export/import metadata as a Frictionless Table Schema (no extra dependency) | `to_table_schema`, `from_table_schema` |
| The same checks as Pandera checks and a ready `SeriesSchema` (optional extra) | `energydata_kit.pandera_checks.series_schema` and check factories |

## Install (from a checkout)

```bash
cd packages/energydata-kit
python -m pip install -e . --group dev   # pip >= 25.1 for --group
pytest
```

Optional Pandera integration: `python -m pip install -e ".[pandera]"`.
Optional Parquet input for the command line: `python -m pip install -e ".[parquet]"`.

## Example

```python
import pandas as pd
import energydata_kit as ek

# Local wall-clock meter readings, including the autumn DST repeat hour.
raw = pd.read_csv("meter.csv")
index = ek.normalize_timestamps(raw["timestamp"], assume_tz="Europe/Stockholm", ambiguous="infer")
series = pd.Series(raw["kwh"].to_numpy(), index=index, name="import_energy")

meta = ek.MeasurementMetadata(
    name="import_energy",
    unit="kWh",
    resolution="15min",
    aggregation="sum",
    interval_label="end",
    timezone="Europe/Stockholm",
)
report = ek.assess_quality(series, metadata=meta, bounds=(0, None))
print(report.to_json())

flagged = ek.flag_series(series, freq="15min", insert_missing=True)
print(flagged[flagged["quality_flag"] != 0])
```

See `examples/basic_quality_report.py` for a runnable version using synthetic data,
and the [guide](examples/GUIDE.md) for worked examples of every feature (DST
timestamps, gaps, flags, metadata, local days, reports, Pandera and the command
line). The test suite runs every code block in the guide.

### Daily or monthly data in local time

A fixed `"1D"` step is 24 hours in UTC, so local midnights look off-grid on DST
days. Use a local-calendar step instead:

```python
idx = ek.normalize_timestamps(daily["date"], assume_tz="Europe/Stockholm")
series = pd.Series(daily["kwh"].to_numpy(), index=idx)
report = ek.assess_quality(series, freq="D", tz="Europe/Stockholm")
monthly = ek.find_missing_intervals(month_index, "MS", tz="Europe/Stockholm")
```

Pass `origin=` (timezone-aware) to fix where any grid starts, e.g. daily
readings at 06:00 local: `origin=pd.Timestamp("2024-01-01 06:00", tz="Europe/Stockholm")`.

## Command line

```bash
energydata-kit report meter.csv \
    --timestamp-col time --value-col kwh \
    --assume-tz Europe/Stockholm --ambiguous infer \
    --freq 15min --unit kWh --aggregation sum --interval-label end \
    --bounds 0 none --flags-csv flagged.csv --fail-on-issues
```

Prints the deterministic JSON report to standard output (`-o` writes a file;
`-` reads the CSV from standard input). A file ending in `.parquet`, `.parq`
or `.pq` is read as Parquet instead (with the `[parquet]` extra), with the
same column options; timestamps may be stored as text or as timestamps, in a
column or as the named index pandas writes with `to_parquet`. `--format text` prints a short summary
for reading instead: rows, completeness, flag counts, the first gaps and
metadata issues per column; `--format markdown` gives the same summary as
Markdown, to paste into an issue or pull request. Use the JSON report for
anything automated. Files separated by `;`, tab or `|` are
read with `--delimiter ';'` (or `--delimiter tab`); `--decimal ,` reads
decimal commas such as `1,5`. `--flags-csv` writes the original rows, in the
same delimiter and decimal format as the input, with a `quality_flag` column, plus inserted rows with `--insert-missing`.
Calendar steps work as in the library: `--freq D --tz Europe/Stockholm`.
Repeat `--value-col` for one report covering several columns (check options
then apply to every column; `--unit` needs a single column). With several
columns, `--flags-csv` writes each value column followed by its
`quality_flag_<column>`. `--schema data.schema.json` reads unit, resolution and
other metadata per column from a Table Schema written by `to_table_schema`;
its columns become the default `--value-col`, and their resolution is the
step when `--freq` is not given.
`energydata-kit compare before.json after.json` prints what changed between
two saved reports (`--format text` or `markdown` for a short summary per column); with `--fail-if-worse` it exits `1` if more rows are
flagged, more intervals are missing or completeness fell.
Exit status: `0` OK, `1` issues found with `--fail-on-issues` or
`--fail-if-worse`, `2` usage, input or file error (for example a directory
given as the CSV, or `-o` in a folder that does not exist). `python -m energydata_kit` is equivalent. See
`energydata-kit report --help` and `energydata-kit compare --help` for every
option.

## Report format

Reports, frame reports and comparisons are JSON with `"schema_version": "2"`
(energydata-kit 0.1.0 wrote `"1"`). The package ships a
[JSON Schema](https://json-schema.org) (draft 2020-12) for all three, in both
schema versions, so tools in any language can validate them:

```python
import json
from importlib import resources

schema = json.loads(resources.files("energydata_kit").joinpath("report_schema.json").read_text())
```

The test suite validates every golden report against it, so the schema and
the code cannot drift apart. Schema 1 is frozen: 0.1.0 reports keep
validating, and `compare_reports` compares them with schema-2 reports (a
count only one side reports, such as `COUNTER_ROLLOVER`, is not compared).
Schema 2 only adds fields; the repository's `docs/architecture/SCHEMA_2.md`
lists them. A further change means schema 3.

## Design rules

- **Keyword options.** Required inputs are positional; every optional
  argument is keyword-only, e.g. `off_grid_mask(index, "15min", origin=...)`.
- **Non-destructive.** No function modifies, fills, drops or reorders input
  values. Flags sit next to the data in a `quality_flag` column.
- **Explicit.** Naive timestamps need a stated time zone. DST ambiguity raises
  unless you choose a policy. Grid checks need a stated step: the step is never
  guessed silently.
- **Deterministic.** Reports contain no wall-clock time or randomness. The same
  input, parameters and package version produce byte-identical JSON, on
  Linux, macOS and Windows: files written with `-o` and `--flags-csv` end
  lines in `\n` everywhere.
- **UTC grid by default.** Sub-daily gap detection runs on a fixed UTC grid, so
  a 23- or 25-hour local DST day is not reported as missing or duplicated
  data. Daily and longer steps in local time use a calendar grid: `tz=`, or
  a metadata resolution such as `"MS"` with its time zone.

## Quality flags

| Bit | Flag | Meaning |
|---|---|---|
| 0 | `OK` | No issue detected |
| 1 | `MISSING_VALUE` | NaN / None / NA at an existing timestamp |
| 2 | `NON_FINITE` | `+inf` or `-inf` |
| 4 | `NON_NUMERIC` | Value cannot be read as a number |
| 8 | `DUPLICATE_TIMESTAMP` | Timestamp occurs more than once (every occurrence is flagged) |
| 16 | `OFF_GRID_TIMESTAMP` | Not aligned to the expected step |
| 32 | `OUT_OF_BOUNDS` | Finite value outside caller-supplied bounds |
| 64 | `MISSING_INTERVAL` | Row inserted for an absent grid timestamp (`insert_missing=True`) |
| 128 | `STALE_VALUE` | Part of a run of at least `stale_min_run` repeated values (opt-in; tune with `stale_atol`, `stale_exclude`) |
| 256 | `COUNTER_DECREASE` | Cumulative counter fell below its previous value (`cumulative=True`, opt-in; tune with `counter_tolerance`) |
| 512 | `JUMP` | Changed by more than `jump_max_delta`, or faster than `jump_max_rate`, from the previous finite value (opt-in) |
| 1024 | `COUNTER_ROLLOVER` | Cumulative counter wrapped past its register modulus `counter_rollover` (opt-in, with `cumulative=True`); flagged instead of `COUNTER_DECREASE` |

Flag values are part of the public API and will not be renumbered.

## Not in scope

Forecasting, grid or power-flow calculations, ratings, optimization, market data
download and resampling/aggregation. For general DataFrame schema validation use
[Pandera](https://pandera.readthedocs.io) (energydata-kit's checks plug into it
via `energydata_kit.pandera_checks`); for unit conversion and unit-aware arrays
use Pint or pint-pandas directly, e.g. `series.astype(f"pint[{meta.unit}]")`.

## Known limitations

- Grids are anchored at the first timestamp unless you pass `origin`, so
  without it a leading off-grid timestamp shifts the grid.
- Calendar steps (`"D"`, `"W-MON"`, `"MS"`, …) passed as `freq` need an
  explicit `tz=`. A metadata resolution with no fixed length (`"MS"`,
  `"W-MON"`) is laid out in `MeasurementMetadata.timezone` when no `freq` or
  `tz` is given; `"D"` in metadata stays a 24-hour step, so pass `tz=`
  (`--tz`) for local days. On a calendar grid the report's per-local-day
  section is `null`.
- A calendar grid whose wall-clock time falls in a skipped or repeated DST hour
  (e.g. daily at 02:30 in Europe/Stockholm) raises, because pandas cannot place
  it.
- Gap, duplicate and off-grid checks run on raw timestamps and do not depend on
  `interval_label`. Only `local_day_completeness` (and the report's
  `local_days` section) uses the label to assign intervals to days.
- Pandera reports failures; it does not flag. In `series_schema` every check
  is attached to the series (not the index) so that lazy validation reports
  index and value failures together, and each gap is reported on the last row
  before it.
- Stale, counter and jump checks compare consecutive rows and ignore time gaps
  between them unless you pass `max_gap` (`--max-gap`, e.g. `"1h"`): then rows
  further apart than that are not compared, so a stale run ends at the gap
  and a drop or jump across it is not flagged. A register reset and a rollover both appear as
  `COUNTER_DECREASE` unless you give the register modulus as `counter_rollover`
  (`--counter-rollover 1e6`): then a drop that wraps past it, with an implied
  increase below half the modulus, is `COUNTER_ROLLOVER`. The modulus is never
  guessed.
- The jump check flags the row where the change lands: a single outlier flags
  itself and the row after it. `jump_max_delta` is an absolute limit per row;
  `jump_max_rate=(delta, period)` (`--jump-max-rate 50 1h`) scales the limit
  by the time since the previous finite value, so it fits any resolution and
  a normal ramp across a gap. Choosing the limit, in the data's own unit, is
  left to the caller.
- Local days that are not a whole number of steps long (e.g. 30-minute DST
  shifts with a 1-hour step) report the floor of the expected count. A day
  shorter than one step (a fixed `"2D"` step, or `"24h"` on a 23-hour DST
  day) expects no interval: its completeness is `NaN` and it is left out of
  the report's `min_completeness`. Use a calendar step (`tz=`) for daily
  data in local time.
- `assess_frame` repeats the timestamp facts (gaps, duplicates) in every
  column's report, because each column's report is exactly what
  `assess_quality` gives for it. The frame-level `timestamps` section
  states them once when all columns share one step; it is `null` when
  columns take different steps from their metadata. `compare_reports`
  compares frames column by column and does not read that section. On the command line, `--unit` works with a
  single `--value-col`; use `--schema` for metadata on several columns.
- `compare_reports` matches gaps by overlap: a gap that shrank, grew or moved
  is listed under `changed` with its before and after bounds (a split or
  merged gap once per overlapping pair), and only gaps overlapping nothing
  are `resolved` or `new`. Only listed gaps are compared; check
  `lists_truncated` when reports capped their lists with `max_listed`.
- Timestamp strings whose UTC offset changes across DST parse quickly in
  the common forms (`2024-03-31T03:00:00+02:00`, or ending in `Z`): about
  0.4 s per 350,000 rows. Other offset forms (`+0200`, `+02`) take pandas'
  general parser, about 2 s per 350,000 rows; pass a `DatetimeIndex` when
  you have one. Measured numbers are in the repository's
  `docs/architecture/PERFORMANCE.md`.
