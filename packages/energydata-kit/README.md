# energydata-kit

Framework-independent quality checks for energy time-series data.

> **Status: pre-alpha (0.1.0.dev0).** Not published. No license has been granted
> yet; see the repository's `docs/governance/RELEASE_GATES.md`.

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
| Stale (flat-line) values and cumulative-counter decreases (opt-in) | `stale_mask`, `counter_decrease_mask` |
| Non-destructive bitmask quality flags | `flag_series`, `QualityFlag`, `decode_flags` |
| Unit and measurement metadata (units parsed by Pint) | `MeasurementMetadata`, `validate_unit`, `units_compatible` |
| Explicit start/end interval relabelling | `relabel_intervals`, `interval_bounds` |
| Unit / aggregation consistency advice | `check_metadata_consistency`, `MetadataIssue` |
| Completeness per local calendar day (DST-aware: 92/96/100 at 15 min) | `local_day_completeness` |
| Reproducible JSON quality reports | `assess_quality`, `QualityReport`, `fingerprint_series` |
| Deterministic synthetic test series | `make_synthetic_series` |
| Export/import metadata as a Frictionless Table Schema (no extra dependency) | `to_table_schema`, `from_table_schema` |
| The same checks as Pandera checks and a ready `SeriesSchema` (optional extra) | `energydata_kit.pandera_checks.series_schema` and check factories |

## Install (from a checkout)

```bash
cd packages/energydata-kit
python -m pip install -e . --group dev   # pip >= 25.1 for --group
pytest
```

Optional Pandera integration: `python -m pip install -e ".[pandera]"`.

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

See `examples/basic_quality_report.py` for a runnable version using synthetic data.

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

## Design rules

- **Non-destructive.** No function modifies, fills, drops or reorders input
  values. Flags sit next to the data in a `quality_flag` column.
- **Explicit.** Naive timestamps need a stated time zone. DST ambiguity raises
  unless you choose a policy. Grid checks need a stated step: the step is never
  guessed silently.
- **Deterministic.** Reports contain no wall-clock time or randomness. The same
  input, parameters and package version produce byte-identical JSON.
- **UTC grid by default.** Sub-daily gap detection runs on a fixed UTC grid, so
  a 23- or 25-hour local DST day is not reported as missing or duplicated
  data. Daily and longer steps in local time use an explicit calendar grid
  (`tz=`).

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
| 128 | `STALE_VALUE` | Part of a run of at least `stale_min_run` repeated values (opt-in) |
| 256 | `COUNTER_DECREASE` | Cumulative counter fell below its previous value (`cumulative=True`, opt-in) |

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
- Calendar steps (`"D"`, `"W-MON"`, `"MS"`, …) need an explicit `tz=`; they are
  never inferred from `MeasurementMetadata.timezone`. With `tz`, the report's
  per-local-day section is skipped.
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
- Stale and counter checks compare consecutive rows and ignore time gaps
  between them. A register reset and a rollover both appear as
  `COUNTER_DECREASE`; telling them apart is left to the caller.
- Local days that are not a whole number of steps long (e.g. 30-minute DST
  shifts with a 1-hour step) report the floor of the expected count.
