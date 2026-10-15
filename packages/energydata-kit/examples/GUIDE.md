# energydata-kit guide

Worked examples, from raw meter timestamps to a reproducible quality report.
All data here is synthetic. Every code block on this page is run by the test
suite (`tests/test_guide.py`), in order, so the outputs shown in the
`assert` lines are real.

Read it top to bottom: later sections reuse variables from earlier ones.

## 1. Timestamps from a local meter

Meters often export local wall-clock time without an offset. On the autumn DST
night the hour 02:00–02:59 happens twice, so the text alone is ambiguous.
energydata-kit never guesses: naive input needs a time zone, and ambiguous
times need a policy.

```python
import io

import numpy as np
import pandas as pd

import energydata_kit as ek

csv = io.StringIO(
    "time,kwh\n"
    "2024-10-27 00:00,1.0\n"
    "2024-10-27 01:00,1.1\n"
    "2024-10-27 02:00,1.2\n"  # first 02:00 (CEST, UTC+2)
    "2024-10-27 02:00,1.3\n"  # second 02:00 (CET, UTC+1)
    "2024-10-27 03:00,1.4\n"
)
raw = pd.read_csv(csv)

try:
    ek.normalize_timestamps(raw["time"], assume_tz="Europe/Stockholm")
except ek.TimestampError as exc:
    print(exc)  # could not localize ... try using the 'ambiguous' argument

# "infer" resolves the repeated hour from the order of the rows.
index = ek.normalize_timestamps(raw["time"], assume_tz="Europe/Stockholm", ambiguous="infer")
assert str(index.tz) == "UTC"
assert index[2].isoformat() == "2024-10-27T00:00:00+00:00"
assert index[3].isoformat() == "2024-10-27T01:00:00+00:00"

summary = ek.summarize_timestamps(index)
assert summary.n_unique == 5 and summary.is_monotonic_increasing
assert summary.inferred_resolution == pd.Timedelta("1h")
```

In UTC the five readings are evenly spaced, one hour apart: nothing is
duplicated and nothing is missing. On the spring night the hour 02:00–02:59
does not exist; `nonexistent="raise"` (the default) rejects such timestamps
instead of silently shifting them.

## 2. Gaps and duplicates

Gap detection runs on a fixed UTC grid with an explicit step.

```python
series = ek.make_synthetic_series(
    start="2024-01-01T00:00Z", periods=96, freq="15min", drop=[10, 11, 12, 60], duplicate=[30]
)

gaps = ek.find_missing_intervals(series.index, "15min")
assert [(g.start.isoformat(), g.missing_count) for g in gaps] == [
    ("2024-01-01T02:30:00+00:00", 3),
    ("2024-01-01T15:00:00+00:00", 1),
]

dups = ek.find_duplicate_timestamps(series.index)
assert [ts.isoformat() for ts in dups] == ["2024-01-01T07:30:00+00:00"]
```

Each `Gap` covers a run of consecutive missing grid timestamps (`start` and
`end` inclusive). The grid starts at the first timestamp; pass
`origin=` to anchor it elsewhere.

## 3. Quality flags

`flag_series` returns a new frame: the original values plus a `quality_flag`
bitmask. Values are never changed, dropped or reordered.

```python
series = ek.make_synthetic_series(periods=8, nan_at=[2], inf_at=[5], drop=[6])
flagged = ek.flag_series(series, freq="15min", bounds=(0, None), insert_missing=True)

assert len(flagged) == len(series) + 1  # one row inserted for the gap
for ts, row in flagged[flagged[ek.FLAG_COLUMN] != 0].iterrows():
    print(ts.isoformat(), ek.decode_flags(row[ek.FLAG_COLUMN]))

assert ek.decode_flags(flagged[ek.FLAG_COLUMN].iloc[2]) == ["MISSING_VALUE"]
assert ek.decode_flags(flagged[ek.FLAG_COLUMN].iloc[5]) == ["NON_FINITE"]
assert ek.decode_flags(flagged[ek.FLAG_COLUMN].iloc[6]) == ["MISSING_VALUE", "MISSING_INTERVAL"]

# Filter with bitwise AND. Use int(...): pandas treats a flag member as a list.
missing = flagged[(flagged[ek.FLAG_COLUMN] & int(ek.QualityFlag.MISSING_VALUE)) != 0]
assert len(missing) == 2
```

The flag values are stable public API; the full table is in the README.

## 4. Units, aggregation and interval labels

`MeasurementMetadata` records what a value means: its unit (parsed by Pint),
how it was aggregated, and whether a timestamp labels the start or the end of
its interval.

```python
meta = ek.MeasurementMetadata(
    name="import_energy",
    unit="kWh",
    resolution="15min",
    aggregation="sum",
    interval_label="end",
    timezone="Europe/Stockholm",
)
assert ek.check_metadata_consistency(meta) == []
assert ek.units_compatible("kWh", "MJ") and not ek.units_compatible("kWh", "kW")

# Power summed over time is a common mistake; the check says so.
suspicious = ek.MeasurementMetadata(name="p", unit="kW", resolution="15min", aggregation="sum")
assert [issue.code for issue in ek.check_metadata_consistency(suspicious)] == ["SUM_OF_POWER"]

try:
    ek.MeasurementMetadata(name="x", unit="kilowatt hourz")
except ek.UnitError as exc:
    print(exc)
```

Converting between start and end labels is explicit, never automatic:

```python
end_labels = pd.DatetimeIndex(["2024-01-01T00:15Z", "2024-01-01T00:30Z"])
start_labels = ek.relabel_intervals(end_labels, "15min", "end", "start")
assert start_labels[0].isoformat() == "2024-01-01T00:00:00+00:00"

bounds = ek.interval_bounds(end_labels, "15min", "end")
print(bounds)  # interval start and end for each row
```

## 5. Completeness per local day

A local day is not always 24 hours. At 15 minutes, Stockholm's spring DST day
has 92 intervals and the autumn day 100.

```python
local = pd.date_range("2024-03-30", "2024-04-01", freq="15min", tz="Europe/Stockholm", inclusive="left")
index = local.tz_convert("UTC")
index = index.delete([100, 101])  # two missing readings on 31 March

days = ek.local_day_completeness(index, "15min", "Europe/Stockholm")
print(days)
assert days["expected"].tolist() == [96, 92]
assert days["missing"].tolist() == [0, 2]
```

## 6. Daily data in local time

A fixed `"1D"` step is 24 hours in UTC, so local midnights would look off-grid
after a DST change. Use a local-calendar step with `tz=` instead:

```python
days_local = pd.date_range("2024-03-28", periods=7, freq="D", tz="Europe/Stockholm")
daily = pd.Series(np.arange(6.0), index=days_local.tz_convert("UTC").delete([4]))

assert ek.off_grid_mask(daily.index, "D", tz="Europe/Stockholm").sum() == 0
gaps = ek.find_missing_intervals(daily.index, "D", tz="Europe/Stockholm")
assert [g.start.isoformat() for g in gaps] == ["2024-03-31T22:00:00+00:00"]  # 1 April, local midnight
```

Grid and gap timestamps are always reported in UTC. Monthly data works the
same way with `"MS"`.

## 7. Opt-in checks: stale values and counters

These need knowledge only the caller has, so they are off by default.

```python
readings = pd.Series(
    [5.0, 5.0, 5.0, 5.0, 6.0, 7.0, 2.0, 3.0],
    index=pd.date_range("2024-01-01", periods=8, freq="1h", tz="UTC"),
)
flags = ek.flag_series(readings, stale_min_run=4, cumulative=True)[ek.FLAG_COLUMN]
assert [ek.decode_flags(f) for f in flags] == [
    ["STALE_VALUE"],
    ["STALE_VALUE"],
    ["STALE_VALUE"],
    ["STALE_VALUE"],
    ["OK"],
    ["OK"],
    ["COUNTER_DECREASE"],  # a reset or a rollover; the caller decides which
    ["OK"],
]
```

## 8. Reproducible reports

`assess_quality` runs every check and returns a report with deterministic
JSON and a SHA-256 fingerprint of the data.

```python
series = ek.make_synthetic_series(periods=96, drop=[10, 11], duplicate=[30], inf_at=[70])
meta = ek.MeasurementMetadata(name="synthetic_power", unit="kW", resolution="15min", aggregation="mean")

report = ek.assess_quality(series, metadata=meta, bounds=(0, None))
assert report.n_gaps == 1 and report.n_missing_intervals == 2
assert report.flag_counts["NON_FINITE"] == 1
assert report.flag_counts["DUPLICATE_TIMESTAMP"] == 2  # both occurrences

# Same input, same parameters, same package version: identical bytes.
again = ek.assess_quality(series.copy(), metadata=meta, bounds=(0, None))
assert again.to_json() == report.to_json()

# The fingerprint ignores how timestamps are displayed.
shown = series.copy()
shown.index = shown.index.tz_convert("Europe/Stockholm")
assert ek.fingerprint_series(shown) == report.fingerprint

print(report.to_json())
```

## 9. Exchanging metadata as a Table Schema

Metadata can travel with a CSV file as a
[Frictionless Table Schema](https://specs.frictionlessdata.io/table-schema/),
with no extra dependency:

```python
import json

schema = ek.to_table_schema(meta, include_flag=True)
print(json.dumps(schema, indent=2))
assert ek.from_table_schema(json.loads(json.dumps(schema))) == meta
```

## 10. Validating with Pandera

With the optional extra (`pip install "energydata-kit[pandera]"`), the same
checks run as a Pandera schema. Pandera reports failures; it does not flag.

<!-- requires: pandera -->
```python
import pandera.pandas as pa

from energydata_kit import pandera_checks

schema = pandera_checks.series_schema(meta, bounds=(0, None))
try:
    schema.validate(series, lazy=True)
except pa.errors.SchemaErrors as exc:
    failed = sorted(set(exc.failure_cases["check"]))
assert failed == [
    "duplicate timestamps",
    "missing intervals after these timestamps at 15min resolution",
    "non-finite or non-numeric values",
]
```

## 11. Command line

The same report for a CSV file, without writing Python. First, a file to
work on:

```python
ek.make_synthetic_series(periods=96, drop=[10, 11], inf_at=[70]).rename("kw").to_frame().to_csv(
    "meter.csv", index_label="timestamp"
)
```

```bash
energydata-kit report meter.csv --freq 15min --unit kW --aggregation mean -o report.json
energydata-kit report meter.csv --freq 15min --flags-csv flagged.csv --insert-missing
# --fail-on-issues makes the exit status usable in pipelines:
energydata-kit report meter.csv --freq 15min --fail-on-issues  # exit status: 1
```

```python
from pathlib import Path

report = json.loads(Path("report.json").read_text())
assert report["n_missing_intervals"] == 2 and report["flag_counts"]["NON_FINITE"] == 1

flagged = pd.read_csv("flagged.csv")
assert len(flagged) == 96 - 2 + 2  # original rows plus the two inserted ones
```

Exit status: `0` OK, `1` issues found with `--fail-on-issues`, `2` usage or
input error. See `energydata-kit report --help` for every option.
