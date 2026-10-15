# Public API review (OSS-13)

**Date:** 2026-10-15 · **Package:** energydata-kit 0.1.0.dev0 · **Scope:**
every name in `energydata_kit.__all__` and `energydata_kit.pandera_checks.__all__`,
plus the report JSON and the command line.

The goal was to settle the calling conventions before 0.1.0, while changing
them still costs nothing: nothing has been released, so no user code depends
on the current signatures.

## Rule adopted

**Required inputs are positional; every optional argument is keyword-only.**

`tests/test_public_api.py` pins the parameter list of every public function
and checks this rule, so a later API change has to update the snapshot on
purpose and be recorded in the CHANGELOG.

## Changes made

All are breaking for positional callers, which is acceptable before the
first release.

| Function | Before | After |
|---|---|---|
| `off_grid_mask` | `origin` positional | keyword-only, like `tz` |
| `expected_grid`, `find_missing_intervals`, `missing_timestamps` | `start`, `end` positional | keyword-only, like `origin` and `tz` |
| `out_of_bounds_mask` | `lower`, `upper` positional | keyword-only (`lower=0` cannot be mistaken for `upper`) |
| `local_day_completeness` | `interval_label` positional | keyword-only |
| `from_table_schema` | `field` positional | keyword-only |
| `MeasurementMetadata` | every field positional | only `name` and `unit` positional; the rest keyword-only, so new fields can be added without breaking callers |
| `pandera_checks.on_grid_check`, `no_missing_intervals_check` | `origin` positional | keyword-only |
| `pandera_checks.within_bounds_check` | `lower`, `upper` positional | keyword-only |
| `pandera_checks.series_schema` | `metadata` positional | keyword-only, matching `assess_quality(series, metadata=...)` |

## Reviewed and kept

- **Names.** Masks end in `_mask` and return boolean NumPy arrays; finders
  start with `find_`; Pandera factories end in `_check`. Options on the
  combined functions carry a check prefix (`stale_min_run`, `jump_max_delta`)
  because they sit next to other checks' options; the single-check functions
  use the short name (`min_run`, `max_delta`).
- **`tz` vs `timezone`.** `tz=` on grid functions means "treat `freq` as a
  local-calendar step in this zone". `MeasurementMetadata.timezone` and the
  required `tz` of `local_day_completeness` describe where the data's local
  days are. The names differ because the meanings differ.
- **Errors.** `TimestampError` and `UnitError` subclass `ValueError`; other
  invalid arguments raise plain `ValueError`. Callers can catch `ValueError`.
- **`QualityFlag` values** stay as they are (0–512) and are never renumbered.
- **Report durations** (`expected_resolution`, `inferred_resolution`) use
  pandas' ISO 8601 form, e.g. `P0DT0H15M0S`. It is verbose but valid and
  unambiguous; changing it would add formatting code for no new information.
- **Command line options** mirror the library names (`--stale-min-run`,
  `--jump-max-delta`, `--bounds LOWER UPPER`).

## Known gaps, not changed

Recorded so that adding them later is a deliberate, additive change:

- `flag_series`, `assess_quality`, `series_schema` and the CLI expose only
  the main option of each opt-in check. `stale_mask(atol=, exclude=)` and
  `counter_decrease_mask(tolerance=)` are available on the mask functions
  only.
- `QualityReport` can be constructed directly, but only `assess_quality` is
  meant to build it; its fields follow report schema 1, which freezes at the
  first release.
