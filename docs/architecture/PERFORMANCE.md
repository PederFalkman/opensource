# Performance

**Measured:** 2026-10-20 (OSS-136), earlier runs on 2026-10-16 (OSS-18),
2026-10-17 (OSS-50) and 2026-10-18 (OSS-74), on one x86_64 CI-class
container. Numbers are wall time (best of 3, measured without memory
tracing) and peak memory traced by Python's `tracemalloc` in one extra run
(includes NumPy and pandas buffers). Before OSS-136 the timed runs were
traced too, which slows Python-level code and made every time read higher;
the table below is the first measured the new way, so its times are lower
than earlier tables for that reason alone. They depend on the
machine; use them for orders of magnitude and compare runs on the same
machine only. Reproduce with `python benchmarks/run.py` from
`packages/energydata-kit`.

Synthetic data: 1 year at 1 min is 525,075 rows; 10 years at 15 min is
350,290 rows. In both, 0.1 % of rows are dropped (gaps) and 0.1 % of values
are NaN.

## Results

| Case | Python 3.13, pandas 3.0.6 (s) | Python 3.11, pandas 2.1.4 (s) | Peak memory (MiB) |
|---|---|---|---|
| `normalize_timestamps`, 350k naive ISO strings | 0.70 | 0.69 | 20–42 |
| `normalize_timestamps`, 350k ISO strings with DST offsets | 0.40 | 0.33 | 41–61 |
| `flag_series`, 1 year at 1 min | 0.02 | 0.02 | 10 |
| `flag_series`, 1 year at 1 min, every check + `insert_missing` | 0.14 | 0.12 | 37 |
| `find_missing_intervals`, 1 year at 1 min | 0.07 | 0.03 | 17 |
| `assess_quality`, 1 year at 1 min | 0.15 | 0.14 | 30–34 |
| `assess_quality`, 10 years at 15 min, every opt-in check | 0.13 | 0.14 | 18–21 |
| `local_day_completeness`, 10 years at 15 min, Europe/Stockholm | 0.02 | 0.04 | 11–14 |
| `assess_frame`, 5 columns, 10 years at 15 min | 0.49 | 0.54 | 18–23 |

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

## Changes in OSS-136

Parsing ISO strings whose UTC offset changes across DST (`+01:00` /
`+02:00`) was the slowest single step: pandas' general parser handles mixed
offsets about 25 times slower than naive strings. `normalize_timestamps` now
splits strings of the strict form `YYYY-MM-DD[T ]HH:MM[:SS[.fff]]` plus `Z`
or `±HH:MM` into local time and offset, parses the local part on pandas'
fast naive path and subtracts the offset. Any other form, and any failure
(including a time pushed past the representable range by its offset), falls
back to the general parser, so results and error messages are unchanged: a
property test compares the two paths, and 120,000 random inputs (both
pandas versions) gave identical results and errors compared with the code
before the change.

Measured on 2026-10-20 without tracing, best of 3, 350,640 strings
(ten years at 15 min in Europe/Stockholm), before → after:

| Case | Python 3.13, pandas 3.0.6 | Python 3.11, pandas 2.1.4 |
|---|---|---|
| `normalize_timestamps`, ISO strings with DST offsets | 2.27 → 0.40 | 2.25 → 0.33 |

Peak memory for that case is higher (41–61 MiB), from the split strings
held during parsing.

## Changes in OSS-144

The same split now covers the `±HHMM` and `±HH` offset forms (P-19), which
still took the general parser. The last six characters of each string
decide the form and the offset and are parsed once per distinct ending, so
the common `±HH:MM` form costs no more than before. As for OSS-136, a
property test compares the fast and general paths, and 120,000 random
batches (both pandas versions, every form plus malformed endings) gave
identical results and errors with the fast path on and off.

Measured on 2026-10-21 without tracing, best of 3, 350,640 strings (ten
years at 15 min in Europe/Stockholm), before → after:

| Offset form | Python 3.13, pandas 3.0.6 | Python 3.11, pandas 2.1.4 |
|---|---|---|
| `+0100` / `+0200` | 2.51 → 0.47 | 2.26 → 0.34 |
| `+01` / `+02` | 2.50 → 0.44 | 2.10 → 0.36 |
| `+01:00` / `+02:00` | 0.38 → 0.39 | 0.31 → 0.33 |

The last row is within run-to-run noise on this machine: in alternating
runs of both versions of the code, best times differed by at most 0.04 s,
and medians overlapped.

## Changes in OSS-74

`assess_quality` built the expected grid twice and tested which grid
timestamps are present two or three times: once for gaps, once for
completeness and once more for known outages. It now builds the grid once
and runs one presence test that all three share. Reports are unchanged
(golden tests); a test checks that the grid is built once.

Measured on 2026-10-18 with `benchmarks/run.py`, the code before and after
this change, side by side on the same machine (best of 3, in seconds):

| Case | Python 3.13, pandas 3.0.6 | Python 3.11, pandas 2.1.4 |
|---|---|---|
| `assess_quality`, 1 year at 1 min | 0.16 → 0.13 | 0.15 → 0.11 |
| `assess_quality`, 10 years at 15 min, every check | 0.18 → 0.16 | 0.14 → 0.12 |
| `assess_frame`, 5 columns, 10 years at 15 min | 0.60 → 0.50 | 0.59 → 0.52 |

Peak memory is the same, within 1 MiB. The other cases do not use this
code, and they changed only within run-to-run noise. Best of 15 runs, the
gain is larger with a local-calendar grid (one year at 1 min with
`tz="Europe/Stockholm"`: 0.16 → 0.11 s on pandas 3) and with known
outages (ten years at 15 min with metadata and one outage: 0.10 → 0.06 s).
With `tz=`, `flag_series` still builds its own grid to flag off-grid
timestamps. Sharing that grid would mean changing `flag_series`, and the
gain does not justify that.

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

- Parsing timestamp strings is pandas' `to_datetime`: about 0.3–0.7 s per
  350k rows, for naive strings or strings with changing offsets in the
  forms `±HH:MM`, `±HHMM`, `±HH` or `Z` (OSS-136, OSS-144). Anything else
  takes the general parser, about 2 s per 350k rows; pass a
  `DatetimeIndex` if you already have one.
- `assess_frame` runs `assess_quality` once per column, so the shared
  timestamp checks are repeated per column (by design, see OSS-17).
- `insert_missing` builds a new, sorted frame with the inserted rows.
