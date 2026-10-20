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
same way with `"MS"`. A metadata resolution with no fixed length, such as
`"MS"` or `"W-MON"`, is laid out in the metadata's time zone when no `freq`
or `tz` is given. `"D"` in metadata stays a 24-hour step, so pass `tz=` for
local days, as above.

```python
month_starts = pd.date_range("2024-01-01", periods=6, freq="MS", tz="Europe/Stockholm")
monthly = pd.Series(np.arange(5.0), index=month_starts.tz_convert("UTC").delete([2]), name="kwh")
monthly_meta = ek.MeasurementMetadata(
    name="kwh", unit="kWh", resolution="MS", aggregation="sum", timezone="Europe/Stockholm"
)
monthly_report = ek.assess_quality(monthly, metadata=monthly_meta)
assert [g.start.isoformat() for g in monthly_report.gaps] == ["2024-02-29T23:00:00+00:00"]  # 1 March, local
assert monthly_report.parameters["tz"] == "Europe/Stockholm"
```

## 7. Opt-in checks: stale values, counters and jumps

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
    ["COUNTER_DECREASE"],  # a reset or a rollover: see counter_rollover below
    ["OK"],
]
```

Both checks can be tuned. `stale_exclude` leaves expected flat runs alone
(e.g. zero generation at night), `stale_atol` treats near-equal values as
repeated, and `counter_tolerance` ignores tiny decreases such as rounding:

```python
solar = pd.Series(
    [0.0, 0.0, 0.0, 0.0, 3.2, 3.2001, 3.1999, 3.2],
    index=pd.date_range("2024-01-01", periods=8, freq="1h", tz="UTC"),
)
flags = ek.flag_series(solar, stale_min_run=4, stale_exclude=[0.0], stale_atol=0.001)[ek.FLAG_COLUMN]
assert [ek.decode_flags(f) for f in flags] == [["OK"]] * 4 + [["STALE_VALUE"]] * 4

meter = pd.Series([100.0, 99.99, 100.5], index=solar.index[:3])
flags = ek.flag_series(meter, cumulative=True, counter_tolerance=0.05)[ek.FLAG_COLUMN]
assert [ek.decode_flags(f) for f in flags] == [["OK"], ["OK"], ["OK"]]
```

The jump check flags a change from the previous valid value larger than a
limit you choose. A single outlier flags two rows: the jump away and the jump
back.

```python
power = pd.Series(
    [10.0, 11.0, 95.0, 12.0, 12.5],
    index=pd.date_range("2024-01-01", periods=5, freq="1h", tz="UTC"),
)
flags = ek.flag_series(power, jump_max_delta=50)[ek.FLAG_COLUMN]
assert [ek.decode_flags(f) for f in flags] == [["OK"], ["OK"], ["JUMP"], ["JUMP"], ["OK"]]
```

An absolute limit suits one resolution. `jump_max_rate=(delta, period)`
scales the limit by the time since the previous valid value instead, so a
normal ramp across a gap is not a jump. Here 20 kW per hour allows 5 kW
between quarter-hours and 60 kW over three hours:

```python
ramp = pd.Series(
    [0.0, 5.0, 10.0, 70.0, 95.0],
    index=pd.DatetimeIndex(
        [
            "2024-01-01T00:00Z",
            "2024-01-01T00:15Z",
            "2024-01-01T00:30Z",
            "2024-01-01T03:30Z",
            "2024-01-01T03:45Z",
        ]
    ),
)
flags = ek.flag_series(ramp, jump_max_rate=(20, "1h"))[ek.FLAG_COLUMN]
assert [ek.decode_flags(f) for f in flags] == [["OK"]] * 4 + [["JUMP"]]  # +25 in 15 minutes
assert ek.flag_series(ramp, jump_max_delta=50)[ek.FLAG_COLUMN].tolist()[3] == ek.QualityFlag.JUMP
```

These checks compare consecutive rows however far apart they are. With
`max_gap`, rows further apart are not compared: a flat line before and after
an outage is two runs, and a counter drop or jump across it is not flagged.

```python
outage = pd.Series(
    [5.0, 5.0, 5.0, 5.0, 5.0],
    index=pd.DatetimeIndex(
        [
            "2024-01-01T00:00Z",
            "2024-01-01T01:00Z",
            "2024-01-01T02:00Z",
            "2024-01-01T09:00Z",
            "2024-01-01T10:00Z",
        ]
    ),
)
assert (ek.flag_series(outage, stale_min_run=4)[ek.FLAG_COLUMN] != 0).all()
assert (ek.flag_series(outage, stale_min_run=4, max_gap="1h")[ek.FLAG_COLUMN] == 0).all()
```

A register that wraps past its size looks like a decrease. If you know the
size (the modulus), pass it as `counter_rollover`: a drop that wraps past it,
by less than half the modulus, is flagged `COUNTER_ROLLOVER` instead. A reset
stays `COUNTER_DECREASE`. The package never guesses a modulus.

```python
register = pd.Series(
    [999_980.0, 999_990.0, 10.0, 500_000.0, 0.0],
    index=pd.date_range("2024-01-01", periods=5, freq="1h", tz="UTC"),
)
flags = ek.flag_series(register, cumulative=True, counter_rollover=1_000_000)[ek.FLAG_COLUMN]
assert [ek.decode_flags(f) for f in flags] == [
    ["OK"],
    ["OK"],
    ["COUNTER_ROLLOVER"],  # 999 990 -> 10 wraps: +20
    ["OK"],
    ["COUNTER_DECREASE"],  # 500 000 -> 0 is a reset
]
```

Reports record these options (`max_gap` as an ISO 8601 duration,
`jump_max_rate` as `[delta, duration]`), so a report states how it was made.

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

Meter exports often hold several channels with one timestamp column.
`assess_frame` gives each column exactly the report `assess_quality` would,
in one deterministic document. Options can differ per column:

```python
channels = pd.DataFrame(
    {
        "power_kw": ek.make_synthetic_series(periods=6, name="power_kw"),
        "energy_kwh": [10.0, 10.4, 10.9, 0.3, 0.8, 1.2],  # register reset at row 3
    }
)
frame_report = ek.assess_frame(
    channels,
    freq="15min",
    per_column={"power_kw": {"bounds": (0, None)}, "energy_kwh": {"cumulative": True}},
)
assert list(frame_report.columns) == ["power_kw", "energy_kwh"]
assert frame_report.summary["energy_kwh"]["n_flagged_rows"] == 1
assert frame_report.columns["energy_kwh"].flag_counts["COUNTER_DECREASE"] == 1

# Flags for every column side by side, one quality_flag_<column> each:
flags = ek.flag_frame(channels, freq="15min", per_column={"energy_kwh": {"cumulative": True}})
assert list(flags.columns) == ["power_kw", "quality_flag_power_kw", "energy_kwh", "quality_flag_energy_kwh"]
assert ek.decode_flags(flags[ek.flag_column("energy_kwh")].iloc[3]) == ["COUNTER_DECREASE"]
```

When a gap was expected, say during maintenance, pass the period as a
known outage. The gap is still reported, but the report says how many
missing intervals it explains and how complete the data is without it:

```python
maintenance = ("2024-01-01T02:30Z", "2024-01-01T02:45Z")  # both ends included
explained = ek.assess_quality(series, metadata=meta, known_outages=[maintenance])
assert explained.n_missing_intervals == 2 and explained.n_missing_explained == 2
assert explained.completeness_excluding_outages == 1.0
```

The command line takes the same periods with `--known-outage START END`,
repeated for several.

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

schema = pandera_checks.series_schema(metadata=meta, bounds=(0, None))
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

After a fix, or when the next delivery of the same feed arrives, compare the
saved reports. Here the gap was filled but the infinite value is still there:

```python
ek.make_synthetic_series(periods=96, inf_at=[70]).rename("kw").to_frame().to_csv(
    "meter_fixed.csv", index_label="timestamp"
)
```

```bash
energydata-kit report meter_fixed.csv --freq 15min --unit kW --aggregation mean -o fixed.json
energydata-kit compare report.json fixed.json -o changes.json --fail-if-worse
```

```python
changes = json.loads(Path("changes.json").read_text())
assert not changes["worse"] and not changes["same_data"]
counts = changes["changes"][""]["counts"]
assert counts["n_missing_intervals"] == {"before": 2, "after": 0, "delta": -2}
assert "NON_FINITE" not in changes["changes"][""].get("flag_counts", {})  # unchanged

# The same comparison in Python, from saved files or report objects:
again = ek.compare_reports(report, json.loads(Path("fixed.json").read_text()))
assert again.to_dict() == changes
```

Gaps are matched by overlap: a gap that shrank, grew or moved is listed under
`changed` with its bounds before and after, not as one resolved and one new
gap.

```python
def gap_report(drop):
    return ek.assess_quality(ek.make_synthetic_series(periods=24, drop=drop), freq="15min")


gaps = ek.compare_reports(gap_report([10]), gap_report([9, 10, 11])).changes[""]["gaps"]
assert gaps["resolved"] == [] and gaps["new"] == []
[pair] = gaps["changed"]
assert (pair["before"]["missing_count"], pair["after"]["missing_count"]) == (1, 3)
```

For a person reading in a terminal, `--format text` prints a short summary
instead of JSON, for reports and comparisons alike. Use JSON for anything
automated.

```bash
energydata-kit report meter.csv --freq 15min --format text -o summary.txt
energydata-kit compare report.json fixed.json --format text -o changes.txt
```

```python
summary = Path("summary.txt").read_text().splitlines()
assert summary[1] == "  completeness: 97.92% (94 of 96 expected); 2 missing in 1 gap(s)"
assert summary[2] == "  flagged rows: 1 (NON_FINITE 1)"

changes_text = Path("changes.txt").read_text().splitlines()
assert changes_text[0] == "data changed; not worse"
assert "missing intervals 2 -> 0 (-2)" in changes_text[2]
```

`--format markdown` gives the same summary as Markdown, ready to paste into
an issue or a pull request:

```bash
energydata-kit compare report.json fixed.json --format markdown -o changes.md
```

```python
changes_md = Path("changes.md").read_text().splitlines()
assert changes_md[:3] == ["# Report comparison", "", "**data changed; not worse**"]
assert any(line.startswith("- rows 94 -> 96 (+2); missing intervals 2 -> 0 (-2)") for line in changes_md)
```

Files exported with semicolons and decimal commas, as many European meter
portals do, are read with `--delimiter` and `--decimal`. The report is the
same as for the comma-separated file, and `--flags-csv` is written in the
input's format:

```python
pd.read_csv("meter.csv").to_csv("meter_eu.csv", sep=";", decimal=",", index=False)
assert ";" in Path("meter_eu.csv").read_text().splitlines()[1]
```

```bash
energydata-kit report meter_eu.csv --delimiter ";" --decimal , \
    --freq 15min --unit kW --aggregation mean -o report_eu.json --flags-csv flagged_eu.csv
```

```python
assert json.loads(Path("report_eu.json").read_text()) == report
assert Path("flagged_eu.csv").read_text().splitlines()[0] == "timestamp;kw;quality_flag"
```

With the optional extra (`pip install "energydata-kit[parquet]"`), a file
ending in `.parquet`, `.parq` or `.pq` is read as Parquet, with the same
options and the same report. Timestamps can be a column or the named index
pandas writes:

<!-- requires: pyarrow -->
```python
pd.read_csv("meter.csv", index_col="timestamp").to_parquet("meter.parquet")
```

<!-- requires: pyarrow -->
```bash
energydata-kit report meter.parquet --freq 15min --unit kW --aggregation mean -o report_pq.json
```

<!-- requires: pyarrow -->
```python
assert json.loads(Path("report_pq.json").read_text()) == report
```

Metadata for one or more columns can come from a Table Schema (section 9)
instead of `--unit`. Its resolution is then the expected step:

```python
schema = ek.to_table_schema(
    ek.MeasurementMetadata(name="kw", unit="kW", resolution="15min", aggregation="mean")
)
Path("meter.schema.json").write_text(json.dumps(schema))
```

```bash
energydata-kit report meter.csv --schema meter.schema.json -o report_schema.json
```

```python
from_schema = json.loads(Path("report_schema.json").read_text())
assert from_schema["metadata"]["unit"] == "kW" and from_schema["n_missing_intervals"] == 2
```

Exit status: `0` OK, `1` issues found with `--fail-on-issues` or
`--fail-if-worse`, `2` usage, input or file error, with the reason on
standard error. See `energydata-kit report --help` for every option.
