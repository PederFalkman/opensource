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
- Report fields `metadata_issues` and `local_days`, and the
  `truncated.incomplete_local_days` flag. The report schema stays at version 1
  because it has not been released yet.
