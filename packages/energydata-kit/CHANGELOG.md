# Changelog

All notable changes to energydata-kit. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [SemVer](https://semver.org/).

## [Unreleased]

### Fixed
- Command line: an unreadable input or unwritable output (a directory, a
  missing parent directory, no permission) ended in a traceback with exit
  status 1, which reads as "issues found"; it now exits 2 with a one-line
  message (OSS-43).

### Fixed
- Local-calendar grids (`tz=`) with an `origin` after the first timestamp
  ran only forward from `origin`, so earlier timestamps were flagged
  off-grid and gaps before `origin` were missed. The grid now runs through
  `origin` in both directions, as fixed-step grids already did (OSS-40).
- `assess_quality` raised `ZeroDivisionError` when `origin` left no grid
  point inside the data's time span; `completeness` is now `None` there.
- A local-calendar grid anchored at a wall-clock time that a DST change
  skips or repeats (e.g. daily at 02:00) now raises a `ValueError` that says
  so, instead of pandas' or pytz's raw error.
- Command line: DST localization errors point to `--ambiguous infer` and
  `--nonexistent`, and `--format text` says how many gaps are not listed
  when `--max-listed` lists fewer than three.
- Unit validation rejected nothing that Pint silently ignores: `"kW?"`,
  `"kWh;"` or `"kW#x"` were accepted as kW/kWh, and `"(kW"` raised an
  uncaught `TokenError`. Such units now raise `UnitError` (OSS-41).
- `MeasurementMetadata(resolution=...)` accepted a `Timedelta`, which made
  `report.to_json()` fail; it now raises `TypeError` asking for a string such
  as `"15min"`.
- `pandera_checks.no_missing_intervals_check` missed a gap at the start when
  the series began off-grid with `origin`, although `assess_quality` counted
  it; it is now reported on the last row before the gap.
- `to_table_schema(..., include_flag=True)` wrote two fields named
  `quality_flag` for a measurement of that name; it now raises `ValueError`.
- `assess_frame` checks that metadata given through `per_column` is named
  after its column, as it already did for `metadata=`.

## [0.1.0] - 2026-10-16

First release: quality checks for metered energy time series, on top of
pandas and Pint. Input data is never modified; checks return masks, flags and
reports.

### Timestamps and grids
- `normalize_timestamps`: UTC normalization with explicit DST policies
  (`ambiguous`, `nonexistent`); naive or unparseable values are reported, not
  guessed (unparseable ones by position).
- `summarize_timestamps` and `infer_resolution`.
- Fixed-step grids: `expected_grid`, `find_missing_intervals`,
  `missing_timestamps`, `find_duplicate_timestamps`, `duplicate_mask` and
  `off_grid_mask`, each with `origin=` to anchor the grid.
- Local-calendar steps via `tz=` (for example `"D"`, `"W-MON"` or `"MS"` in
  `"Europe/Stockholm"`), DST-aware.
- Interval semantics: `relabel_intervals` and `interval_bounds` for start/end
  labels; `local_day_completeness` per local calendar day.

### Values and flags
- Masks for missing, non-finite, non-numeric and out-of-bounds values, plus
  the opt-in `stale_mask`, `counter_decrease_mask` and `jump_mask`, tuned with
  `stale_atol`, `stale_exclude`, `counter_tolerance` and `jump_max_delta`.
- `QualityFlag` bitmask (`MISSING_VALUE` = 1 up to `JUMP` = 512) and the
  non-destructive `flag_series`; `flag_frame` and `flag_column` for several
  columns at once.

### Metadata
- `MeasurementMetadata`: unit (validated with Pint, including `var`),
  resolution, aggregation, interval label and time zone.
- `check_metadata_consistency` returning `MetadataIssue`s with the stable codes
  `SUM_OF_POWER`, `AVERAGED_ENERGY`, `MISSING_RESOLUTION` and
  `LABEL_ON_INSTANTANEOUS`.
- `to_table_schema` / `from_table_schema`: Frictionless Table Schema export and
  import, under a namespaced `"energydata_kit"` field property.

### Reports
- `assess_quality` → `QualityReport`: deterministic JSON (report schema 1)
  with a SHA-256 data fingerprint, the parameters used, metadata issues and
  per-local-day completeness.
- `assess_frame` → `FrameQualityReport`: one report for several columns that
  share a timestamp index, with per-column options; each column's section
  equals `assess_quality` on that column.
- `compare_reports` → `ReportComparison`: what changed between two reports
  (objects or saved JSON), with deltas, resolved and new gaps, and a `worse`
  verdict.

### Command line
`energydata-kit` (also `python -m energydata_kit`); exit status 0 OK, 1 issues
found on request, 2 usage or input error.
- `report`: JSON report for one or more CSV columns, every check option,
  `--flags-csv`, `--fail-on-issues` and `--format text` for a readable
  summary. Metadata from `--unit` (one column) or `--schema` (a Table Schema,
  any number of columns). `--delimiter` and `--decimal` read `;`-, tab- or
  `|`-separated files with decimal commas; the flags CSV follows the input's
  format.
- `compare`: what changed between two saved reports, with `--fail-if-worse`
  and `--format text`.

### Integrations and documentation
- Optional extra `[pandera]`: `energydata_kit.pandera_checks` with check
  factories and `series_schema(...)`, built on the same masks as
  `flag_series`.
- `make_synthetic_series` for deterministic test data.
- `examples/GUIDE.md`: worked examples from raw local meter timestamps to
  reports and the command line, executed by the test suite.

### Conventions
- Required inputs are positional and every optional argument is keyword-only;
  the public signatures are pinned by `tests/test_public_api.py`.
- `assess_quality` on a year of one-minute data takes about a quarter of a
  second on the benchmark machine (`docs/architecture/PERFORMANCE.md`).
