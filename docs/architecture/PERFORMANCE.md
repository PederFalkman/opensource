# Performance

**Measured:** 2026-10-16 (OSS-18), re-measured 2026-10-17 (OSS-50) after
the input checks added in OSS-40 to OSS-49, on one x86_64 CI-class container.
Numbers are wall time (best of 3) and peak memory traced by Python's
`tracemalloc` (includes NumPy and pandas buffers). They depend on the
machine; use them for orders of magnitude and compare runs on the same
machine only. Reproduce with `python benchmarks/run.py` from
`packages/energydata-kit`.

Synthetic data: 1 year at 1 min is 525,075 rows; 10 years at 15 min is
350,290 rows. In both, 0.1 % of rows are dropped (gaps) and 0.1 % of values
are NaN.

## Results

| Case | Python 3.13, pandas 3.0.6 (s) | Python 3.11, pandas 2.1.4 (s) | Peak memory (MiB) |
|---|---|---|---|
| `normalize_timestamps`, 350k naive ISO strings | 0.80 | 0.88 | 20–22 |
| `flag_series`, 1 year at 1 min | 0.02 | 0.02 | 10–26 |
| `flag_series`, 1 year at 1 min, every check + `insert_missing` | 0.14 | 0.11 | 37 |
| `find_missing_intervals`, 1 year at 1 min | 0.11 | 0.05 | 17 |
| `assess_quality`, 1 year at 1 min | 0.21 | 0.17 | 29–33 |
| `assess_quality`, 10 years at 15 min, every opt-in check | 0.20 | 0.19 | 17–20 |
| `local_day_completeness`, 10 years at 15 min, Europe/Stockholm | 0.06 | 0.12 | 11–14 |
| `assess_frame`, 5 columns, 10 years at 15 min | 0.83 | 0.75 | 17–31 |

Everything scales linearly with the number of rows (and, for
`assess_frame`, with the number of columns). The coarse guard in
`tests/test_performance.py` fails if `assess_quality` on a year of minute
data takes more than 10 seconds, which only a real regression (for example
an accidental quadratic step) would cause.

The OSS-50 re-run found no regression, and peak memory was unchanged. Two
cases read slightly slower than on 2026-10-16 (`local_day_completeness` on
3.11, `find_missing_intervals` on 3.13); timed side by side on the same
machine, the code before OSS-40 was no faster in either, so that is
run-to-run noise. `compare_reports`, which validates
its input since OSS-47, takes about 0.4 ms for two reports with 350 listed
gaps each.

## Changes in OSS-18

On Python 3.13 with pandas 3, before → after:

| Case | Before (s) | After (s) |
|---|---|---|
| `normalize_timestamps`, 350k naive ISO strings | 1.45 | 0.95 |
| `assess_quality`, 1 year at 1 min | 0.64 | 0.27 |
| `assess_frame`, 5 columns, 10 years at 15 min | 1.70 | 1.00 |
| `find_missing_intervals`, 1 year at 1 min | 0.15 | 0.10 |

- **Nanosecond conversion without copying.** pandas 3 creates microsecond
  indexes by default, and converting a whole index to nanoseconds copies it.
  `utc_ns` now reads the index's own integers and scales them, still raising
  for out-of-range timestamps.
- **Sorted search instead of hashing** to test which grid timestamps are
  present (gaps, completeness, off-grid on calendar grids, Pandera gap
  check). Same results; a test compares it with `isin`.
- **Vectorised time-zone detection** for string timestamps in
  `normalize_timestamps`, instead of a regular expression per value.

On pandas 2.1 the differences are within noise: there, the copies and hashing
removed above were already cheap.

## What dominates now

- Parsing timestamp strings is pandas' `to_datetime`. ISO strings with UTC
  offsets that change across DST (e.g. `+01:00` / `+02:00`) take about 2 s
  per 350k rows in pandas itself; pass a `DatetimeIndex` if you already have
  one.
- `assess_frame` runs `assess_quality` once per column, so the shared
  timestamp checks are repeated per column (by design, see OSS-17).
- `insert_missing` builds a new, sorted frame with the inserted rows.
