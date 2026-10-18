# Changelog

All notable changes to energydata-kit. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [SemVer](https://semver.org/).

## [Unreleased]

### Added
- Parquet input for `energydata-kit report`: a file ending in `.parquet`,
  `.parq` or `.pq` is read with pandas and pyarrow, with the same column
  options and the same report as the CSV of the same data. pyarrow comes
  with the new optional extra `[parquet]` (`pyarrow>=14.0.1`, which fixes
  CVE-2023-47248); without it the command says what to install and exits
  2. `--delimiter` and `--decimal` are refused for Parquet (OSS-58).
- Frame reports have a `timestamps` section: the facts that depend only on
  the shared timestamp index (rows, range, step, completeness, gaps,
  duplicates, known-outage figures), stated once when every column reports
  the same ones, `null` when columns take different steps from their
  metadata. Column reports are unchanged and still equal `assess_quality`
  on each column. Part of report schema 1 and its JSON Schema (OSS-57).
- Known outages: `assess_quality(..., known_outages=[(start, end), ...])`,
  `assess_frame(..., known_outages=...)` and `energydata-kit report
  --known-outage START END` take periods in which data is known to be
  missing. Reports gain `n_missing_explained` (missing intervals inside
  those periods), `completeness_excluding_outages` and
  `parameters.known_outages`; gaps, totals, completeness and flags are
  unchanged. `compare_reports` and the text and Markdown summaries show the
  new figures. The fields are part of report schema 1, which is fixed from
  the 0.1.0 release on (OSS-56).
- `--format markdown` for `energydata-kit report` and `compare`: the same
  summary as `--format text`, as Markdown headings and bullet lists to
  paste into an issue or pull request. Column names are escaped. Built
  from the same facts as the text summary, whose output is unchanged
  (OSS-55).
- `report_schema.json`: a JSON Schema (draft 2020-12) for report schema 1,
  covering single-series reports, frame reports and comparisons. It ships in
  the package; the tests validate every golden report and a set of generated
  ones against it (OSS-54).
- Python 3.14 is tested in CI and declared in the package classifiers; the
  test suite, including the byte-for-byte golden reports, passes unchanged
  (OSS-51).

### Fixed
- Command line on Windows: `-o` files and `--flags-csv` were written with
  `\r\n` line endings, so reports were not byte-identical to those made on
  Linux or macOS. Both now end lines in `\n` on every platform; the tests
  run on Windows and macOS in CI (OSS-52).
- `from_table_schema` (and `energydata-kit report --schema`) let a `name`
  inside the `energydata_kit` property override the field's own name, so
  the report for one column carried metadata named after another. Such a
  schema is now rejected, and every malformed schema (not an object, a
  field without a name, a non-object or incomplete `energydata_kit`
  property) raises `ValueError` naming the problem instead of `KeyError`,
  `AttributeError` or an internal `TypeError` (OSS-49).

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
- `MeasurementMetadata`: unit (validated with Pint, including `var`; units
  with characters Pint would silently drop are rejected), resolution,
  aggregation, interval label and time zone.
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
  verdict. Input that is not a report, such as a saved comparison, is
  rejected with the first bad field named.

### Command line
`energydata-kit` (also `python -m energydata_kit`); exit status 0 OK, 1 issues
found on request, 2 usage, input or file error (listed in `--help`).
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
- Invalid input raises `ValueError` or `TypeError` with the reason (for
  example a `NaT` timestamp or a flag value no flag uses), never a silent
  guess.
- Reports, flags CSVs and fingerprints are byte-identical on every
  supported Python, pandas and numpy version, pinned by golden tests.
- `assess_quality` on a year of one-minute data takes about a quarter of a
  second on the benchmark machine (`docs/architecture/PERFORMANCE.md`).
