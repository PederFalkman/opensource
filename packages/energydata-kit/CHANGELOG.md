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
