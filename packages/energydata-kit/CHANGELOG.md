# Changelog

All notable changes to energydata-kit. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [SemVer](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-10-18

First release: quality checks for metered energy time series, on top of
pandas and Pint. Input data is never modified; checks return masks, flags and
reports. Licensed Apache-2.0; the licence ships in the wheel and the sdist.

### Timestamps and grids
- `normalize_timestamps`: UTC normalization with explicit DST policies
  (`ambiguous`, `nonexistent`); naive or unparseable values are reported, not
  guessed (unparseable ones by position). A date without a time of day is
  naive and needs `assume_tz`.
- `summarize_timestamps` and `infer_resolution`.
- Fixed-step grids: `expected_grid`, `find_missing_intervals`,
  `missing_timestamps`, `find_duplicate_timestamps`, `duplicate_mask` and
  `off_grid_mask`, each with `origin=` to anchor the grid.
- Local-calendar steps via `tz=` (for example `"D"`, `"W-MON"` or `"MS"` in
  `"Europe/Stockholm"`), DST-aware.
- Interval semantics: `relabel_intervals` and `interval_bounds` for start/end
  labels; `local_day_completeness` per local calendar day, on the same grid
  as the report (`origin=` included).

### Values and flags
- Masks for missing, non-finite, non-numeric and out-of-bounds values, plus
  the opt-in `stale_mask`, `counter_decrease_mask` and `jump_mask`, tuned with
  `stale_atol`, `stale_exclude`, `counter_tolerance` and `jump_max_delta`
  (a run is excluded when all its values lie within `stale_atol` of an
  excluded value).
- `QualityFlag` bitmask (`MISSING_VALUE` = 1 up to `JUMP` = 512) and the
  non-destructive `flag_series`; `flag_frame` and `flag_column` for several
  columns at once.

### Metadata
- `MeasurementMetadata`: unit (validated with Pint, including `var`; units
  with characters Pint would silently drop are rejected), resolution,
  aggregation, interval label and time zone.
- `check_metadata_consistency` returning `MetadataIssue`s with the stable codes
  `SUM_OF_POWER`, `AVERAGED_ENERGY`, `MISSING_RESOLUTION` and
  `LABEL_ON_INSTANTANEOUS`.
- `to_table_schema` / `from_table_schema`: Frictionless Table Schema export and
  import, under a namespaced `"energydata_kit"` field property. A malformed
  schema raises `ValueError` naming the problem; a `name` inside the
  namespace, which would relabel the field, is rejected.

### Reports
- `assess_quality` → `QualityReport`: deterministic JSON (report schema 1)
  with a SHA-256 data fingerprint, the parameters used, metadata issues and
  per-local-day completeness. Without `freq`, the step is the metadata
  resolution; one with no fixed length (`"MS"`, `"W-MON"`) counts in the
  metadata's time zone. `"D"` is a 24-hour step; for local days, which are
  23 or 25 hours long across DST, pass `tz` (`--tz`).
- `assess_frame` → `FrameQualityReport`: one report for several columns that
  share a timestamp index, with per-column options; each column's section
  equals `assess_quality` on that column. A `timestamps` section states the
  facts that depend only on the shared index (rows, range, step,
  completeness, gaps, duplicates, known-outage figures) once, or is `null`
  when columns take different steps from their metadata.
- Known outages: `known_outages=[(start, end), ...]` lists periods in which
  data is known to be missing. Reports count the missing intervals inside
  them (`n_missing_explained`) and give `completeness_excluding_outages`;
  gaps, totals, completeness and flags are unchanged.
- `compare_reports` → `ReportComparison`: what changed between two reports
  (objects or saved JSON), with deltas, resolved and new gaps, and a `worse`
  verdict. Input that is not a report, such as a saved comparison, is
  rejected with the first bad field named.
- `report_schema.json`: a JSON Schema (draft 2020-12) for report schema 1,
  covering single-series reports, frame reports and comparisons; it ships in
  the package. Schema 1 is fixed from this release on.

### Command line
`energydata-kit` (also `python -m energydata_kit`); exit status 0 OK, 1 issues
found on request, 2 usage, input or file error (listed in `--help`).
- `report`: JSON report for one or more CSV columns, every check option,
  `--known-outage START END`, `--flags-csv`, `--fail-on-issues`, and
  `--format text` or `markdown` for a readable summary (Markdown to paste
  into an issue or pull request; column names escaped and kept on one
  line; when completeness is missing, the summary says why). Metadata from `--unit` (one column, with `--resolution`,
  `--aggregation`, `--interval-label` and `--timezone`) or `--schema` (a
  Table Schema, any number of columns). `--delimiter` and `--decimal` read `;`-, tab- or
  `|`-separated files with decimal commas; the flags CSV follows the input's
  format.
- Parquet input: a file ending in `.parquet`, `.parq` or `.pq` is read with
  the optional extra `[parquet]` (`pyarrow>=14.0.1`) and gives the same
  report as the CSV of the same data. Timestamps may be a column or the
  named index pandas writes with `to_parquet`; unreadable files and
  directories are refused with exit status 2.
- `compare`: what changed between two saved reports, with `--fail-if-worse`
  and `--format text` or `markdown`.

### Integrations and documentation
- Optional extra `[pandera]`: `energydata_kit.pandera_checks` with check
  factories and `series_schema(...)`, built on the same masks as
  `flag_series`; Pandera 0.24 or later, tested on the lowest and the latest.
- `make_synthetic_series` for deterministic test data.
- `examples/GUIDE.md`: worked examples from raw local meter timestamps to
  reports and the command line, executed by the test suite.

### Conventions
- Required inputs are positional and every optional argument is keyword-only;
  the public signatures are pinned by `tests/test_public_api.py`.
- Invalid input raises `ValueError` or `TypeError` with the reason (for
  example a `NaT` timestamp, a flag value no flag uses or a non-finite
  bound or tolerance), never a silent guess. Options are checked when they
  are given, also for empty data and when a Pandera check is built:
  numeric options take real numbers (numpy ones included) but not booleans
  or text, `cumulative` takes `True` or `False`, run lengths and
  `max_listed` take integers, and `tz` must name a known time zone.
- Python 3.11 to 3.14, tested on Linux, Windows and macOS.
- Reports, flags CSVs and fingerprints are byte-identical on every
  supported Python, pandas and numpy version and on every platform (files
  end lines in `\n`), pinned by golden tests.
- `assess_quality` on a year of one-minute data takes under a quarter of a
  second on the benchmark machine (`docs/architecture/PERFORMANCE.md`).
