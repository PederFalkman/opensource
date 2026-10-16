# Changelog

All notable changes to energydata-kit. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [SemVer](https://semver.org/).

## [Unreleased]

### Added
- Command line (OSS-28): `--delimiter` reads files separated by `;`, tab
  (`--delimiter tab`) or `|`, and `--decimal ,` reads decimal commas, common
  in European meter exports. The report is identical to that of the same data
  as a comma-separated file, and `--flags-csv` is written in the same format
  as the input (OSS-30). The single-column hint now suggests the matching
  `--delimiter`.
- Command line (OSS-32): `report --format text` prints a short readable
  summary (rows, completeness, flag counts, first gaps, metadata issues per
  column) instead of the JSON report. JSON stays the default and unchanged.

### Changed
- Clearer errors for awkward input (OSS-27): timestamps that are not ISO 8601
  are named with their position (`could not parse 1 timestamp(s) as ISO 8601
  (position 0: 'not-a-date')`) instead of pandas' parser hint, and in a mix
  with timezone-aware values they are no longer miscounted as naive. The
  command line suggests checking the delimiter when a file reads as a single
  `;`-, tab- or `|`-separated column. The `assess_quality` docstring states
  that completeness counts timestamps, not values.

## [0.1.0] - 2026-10-16

### Changed
- Pre-release polish (OSS-20): every public function, class, method and
  property has a docstring (now checked in CI); `fingerprint_series` gives the
  same `normalize_timestamps()` hint as the other timezone errors; README
  limitations cover multi-column reports, report comparison and slow
  offset-string parsing.
- Faster on long series, same results (OSS-18): nanosecond timestamps are read
  without copying the index, grid membership uses a sorted search, and string
  timestamps are checked for UTC offsets vectorised. With pandas 3,
  `assess_quality` on a year of minute data went from 0.64 s to 0.27 s. See
  `docs/architecture/PERFORMANCE.md`.
- Pre-release API review (OSS-13): required inputs are positional and every
  optional argument is keyword-only. Affects `off_grid_mask(origin=)`,
  `expected_grid` / `find_missing_intervals` / `missing_timestamps`
  (`start=`, `end=`), `out_of_bounds_mask(lower=, upper=)`,
  `local_day_completeness(interval_label=)`, `from_table_schema(field=)`,
  `MeasurementMetadata` (fields after `name` and `unit`) and the Pandera
  factories `on_grid_check`, `no_missing_intervals_check`,
  `within_bounds_check` and `series_schema(metadata=)`. The public signatures
  are pinned by `tests/test_public_api.py`. See
  `docs/architecture/API_REVIEW.md`.

### Added
- `normalize_timestamps`: tz-aware UTC normalization with explicit DST policies.
- `summarize_timestamps`, `infer_resolution`.
- `find_missing_intervals`, `expected_grid`, `find_duplicate_timestamps`,
  `duplicate_mask`, `off_grid_mask` on fixed-step UTC grids.
- Value masks: missing, non-finite, non-numeric, out-of-bounds.
- `QualityFlag` bitmask (values 0–64) and non-destructive `flag_series`.
- `MeasurementMetadata` with Pint-based unit validation (plus `var`).
- `assess_quality` → `QualityReport` with deterministic JSON (schema 1) and
  SHA-256 data fingerprint.
- `make_synthetic_series` for deterministic test data.
- `relabel_intervals` and `interval_bounds` for explicit start/end label
  conversion (OSS-02).
- `check_metadata_consistency` returning `MetadataIssue`s with stable codes
  `SUM_OF_POWER`, `AVERAGED_ENERGY`, `MISSING_RESOLUTION`,
  `LABEL_ON_INSTANTANEOUS` (OSS-02).
- `local_day_completeness`: expected vs. present intervals per local calendar
  day, DST-aware (OSS-02).
- `stale_mask` and `counter_decrease_mask`, with new flags `STALE_VALUE` (128)
  and `COUNTER_DECREASE` (256). Both are opt-in via `stale_min_run` and
  `cumulative` on `flag_series` and `assess_quality` (OSS-03).
- `to_table_schema` / `from_table_schema`: Frictionless Table Schema export and
  import of `MeasurementMetadata`, stored under a namespaced
  `"energydata_kit"` field property (OSS-04).
- Optional extra `[pandera]` with `energydata_kit.pandera_checks`: Pandera
  check factories and `series_schema(...)` built on the same masks as
  `flag_series` (OSS-04).
- Grid `origin=` on `expected_grid`, `off_grid_mask`, `find_missing_intervals`,
  `flag_series`, `assess_quality` and the Pandera grid checks, so a leading
  off-grid timestamp no longer shifts the grid (OSS-05).
- Local-calendar steps via `tz=` (e.g. `"D"`, `"W-MON"`, `"MS"` in
  `"Europe/Stockholm"`), DST-aware; `missing_timestamps`; calendar values
  accepted in `MeasurementMetadata.resolution`. Report `parameters` record
  `origin` and `tz` (OSS-05).
- `energydata-kit report` command line (also `python -m energydata_kit`):
  JSON report for one CSV column, optional flagged CSV, `--fail-on-issues`
  exit status for pipelines. Standard-library `argparse`; no new
  dependency (OSS-07).
- Property-based tests (Hypothesis, dev-only) for the core guarantees:
  non-destructive flagging, flag bits matching the individual masks, gap
  accounting, deterministic reports, fingerprint invariance, label round
  trips, stale/counter masks against brute-force references, local-day
  bounds and Table Schema round trips (OSS-10).
- `jump_mask` and the opt-in flag `JUMP` (512): a value that differs from the
  previous finite value by more than a caller-supplied `jump_max_delta`.
  Available on `flag_series`, `assess_quality` (recorded in report
  `parameters`), the CLI (`--jump-max-delta`) and Pandera (`jump_check`,
  `series_schema(jump_max_delta=...)`) (OSS-11).
- Tuning options for the opt-in checks on `flag_series`, `assess_quality`
  and `pandera_checks.series_schema`: `stale_atol`, `stale_exclude` and
  `counter_tolerance`, also as CLI `--stale-atol`, `--stale-exclude` and
  `--counter-tolerance`. Recorded in report `parameters`; giving one without
  its check raises `ValueError` (OSS-15).
- `assess_frame` → `FrameQualityReport`: one deterministic report for several
  columns sharing a timestamp index. Each column's section equals
  `assess_quality` on that column; shared options apply to all columns and
  `per_column` overrides check options and metadata per column. Combined
  fingerprint and a per-column summary. CLI: repeat `--value-col` (OSS-17).
- `compare_reports` → `ReportComparison`: what changed between two reports
  (objects or saved JSON), with deltas for counts and flag counts, resolved and
  new listed gaps, metadata issues and changed parameters or metadata; frame
  reports per column. `worse` is true if more rows are flagged, more intervals
  are missing or completeness fell. CLI: `energydata-kit compare BEFORE AFTER`
  with `--fail-if-worse` (OSS-19).
- `flag_frame` and `flag_column`: flags for several columns at once, each
  column's `quality_flag_<column>` exactly what `flag_series` gives for it;
  `insert_missing` adds absent rows once. The CLI's `--flags-csv` now works
  with several `--value-col` (OSS-21).
- `examples/GUIDE.md`: worked examples from raw local meter timestamps to a
  reproducible report, the command line and Pandera. `tests/test_guide.py`
  runs every code block, so the guide fails CI when it goes stale (OSS-12).
- Report fields `metadata_issues` and `local_days`, and the
  `truncated.incomplete_local_days` flag. The report schema stays at version 1
  because it has not been released yet.
