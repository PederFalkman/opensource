# Changelog

All notable changes to energydata-kit. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [SemVer](https://semver.org/).

## [Unreleased]

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
- `examples/GUIDE.md`: worked examples from raw local meter timestamps to a
  reproducible report, the command line and Pandera. `tests/test_guide.py`
  runs every code block, so the guide fails CI when it goes stale (OSS-12).
- Report fields `metadata_issues` and `local_days`, and the
  `truncated.incomplete_local_days` flag. The report schema stays at version 1
  because it has not been released yet.
