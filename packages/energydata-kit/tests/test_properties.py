"""Property-based tests for the package's core guarantees (Hypothesis).

Runs deterministically: ``derandomize=True`` derives examples from the test
itself and the example database is disabled, so CI and local runs see the
same cases. Skipped when Hypothesis is not installed (e.g. the clean-wheel
test in CI).
"""

from __future__ import annotations

import itertools
import json

import numpy as np
import pandas as pd
import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import HealthCheck, given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402

from energydata_kit import (  # noqa: E402
    FLAG_COLUMN,
    VALUE_COLUMN,
    Aggregation,
    IntervalLabel,
    MeasurementMetadata,
    QualityFlag,
    assess_quality,
    counter_decrease_mask,
    duplicate_mask,
    expected_grid,
    find_missing_intervals,
    fingerprint_series,
    flag_series,
    from_table_schema,
    jump_mask,
    local_day_completeness,
    missing_timestamps,
    missing_value_mask,
    non_finite_mask,
    normalize_timestamps,
    off_grid_mask,
    out_of_bounds_mask,
    relabel_intervals,
    stale_mask,
    to_table_schema,
)

DETERMINISTIC = settings(
    derandomize=True,
    database=None,
    deadline=None,
    max_examples=75,
    suppress_health_check=[HealthCheck.too_slow],
)

STEP = pd.Timedelta("15min")
START = pd.Timestamp("2024-03-30T00:00Z")  # covers the 2024-03-31 Stockholm DST change

values = st.floats(allow_nan=True, allow_infinity=True, width=32)


@st.composite
def grid_series(draw, max_slots: int = 200, duplicates: bool = True, off_grid: bool = False) -> pd.Series:
    """A sorted UTC series on a 15-min grid with random gaps, duplicates and values."""
    n_slots = draw(st.integers(min_value=1, max_value=max_slots))
    keep = sorted(draw(st.sets(st.integers(0, n_slots - 1), min_size=1, max_size=n_slots)))
    stamps = [START + k * STEP for k in keep]
    if duplicates:
        stamps += draw(st.lists(st.sampled_from(stamps), max_size=5))
    if off_grid:
        stamps += [s + pd.Timedelta(minutes=7) for s in draw(st.lists(st.sampled_from(stamps), max_size=3))]
    index = pd.DatetimeIndex(sorted(stamps)).as_unit("ns")
    data = draw(st.lists(values, min_size=len(index), max_size=len(index)))
    return pd.Series(np.asarray(data, dtype="float64"), index=index, name="x")


@DETERMINISTIC
@given(grid_series(off_grid=True), st.booleans())
def test_flag_series_never_changes_values_or_rows(series, insert_missing):
    before = series.copy(deep=True)
    out = flag_series(series, freq=STEP, insert_missing=insert_missing)
    pd.testing.assert_series_equal(series, before)
    original = out[(out[FLAG_COLUMN] & int(QualityFlag.MISSING_INTERVAL)) == 0]
    assert original.index.equals(series.index)
    np.testing.assert_array_equal(original[VALUE_COLUMN].to_numpy(dtype=float), series.to_numpy())


@DETERMINISTIC
@given(
    grid_series(off_grid=True),
    st.one_of(st.none(), st.floats(-1e3, 1e3)),
    st.integers(2, 4),
    st.floats(1e-3, 1e6),
)
def test_flag_bits_equal_the_individual_masks(series, upper, min_run, max_delta):
    flags = flag_series(
        series,
        freq=STEP,
        bounds=(None, upper),
        stale_min_run=min_run,
        cumulative=True,
        jump_max_delta=max_delta,
    )
    flags = flags[FLAG_COLUMN].to_numpy()
    expected = (
        missing_value_mask(series) * int(QualityFlag.MISSING_VALUE)
        | non_finite_mask(series) * int(QualityFlag.NON_FINITE)
        | duplicate_mask(series.index) * int(QualityFlag.DUPLICATE_TIMESTAMP)
        | off_grid_mask(series.index, STEP) * int(QualityFlag.OFF_GRID_TIMESTAMP)
        | out_of_bounds_mask(series, None, upper) * int(QualityFlag.OUT_OF_BOUNDS)
        | stale_mask(series, min_run) * int(QualityFlag.STALE_VALUE)
        | counter_decrease_mask(series) * int(QualityFlag.COUNTER_DECREASE)
        | jump_mask(series, max_delta) * int(QualityFlag.JUMP)
    )
    np.testing.assert_array_equal(flags, expected)


@DETERMINISTIC
@given(grid_series())
def test_gap_accounting_adds_up(series):
    grid = expected_grid(series.index, STEP)
    gaps = find_missing_intervals(series.index, STEP)
    missing = missing_timestamps(series.index, STEP)
    present = int(grid.isin(series.index).sum())
    assert present + sum(g.missing_count for g in gaps) == len(grid)
    assert len(missing) == sum(g.missing_count for g in gaps)
    # Gaps are ordered, disjoint and separated by at least one present slot.
    for earlier, later in itertools.pairwise(gaps):
        assert later.start - earlier.end > STEP
    # Inserting the missing rows leaves nothing missing.
    filled = flag_series(series, freq=STEP, insert_missing=True)
    assert len(filled) == len(series) + len(missing)
    assert find_missing_intervals(pd.DatetimeIndex(filled.index), STEP) == []


@DETERMINISTIC
@given(grid_series(off_grid=True), st.integers(0, 3))
def test_report_is_deterministic_and_counts_match(series, max_listed):
    a = assess_quality(series, freq=STEP, max_listed=max_listed)
    b = assess_quality(series.copy(), freq=STEP, max_listed=max_listed)
    assert a.to_json() == b.to_json()
    data = json.loads(a.to_json())
    assert data["n_rows"] == len(series)
    assert len(data["gaps"]) == min(data["n_gaps"], max_listed)
    assert data["truncated"]["gaps"] == (data["n_gaps"] > max_listed)
    if data["n_expected_intervals"]:
        assert 0.0 <= data["completeness"] <= 1.0


@DETERMINISTIC
@given(grid_series(), st.sampled_from(["UTC", "Europe/Stockholm", "America/New_York"]))
def test_fingerprint_ignores_display_zone_and_unit(series, zone):
    shown = series.copy()
    shown.index = shown.index.tz_convert(zone).as_unit("us")
    assert fingerprint_series(shown) == fingerprint_series(series)


@DETERMINISTIC
@given(grid_series(duplicates=True))
def test_relabel_round_trip(series):
    idx = series.index
    there = relabel_intervals(idx, STEP, IntervalLabel.START, IntervalLabel.END)
    assert relabel_intervals(there, STEP, IntervalLabel.END, IntervalLabel.START).equals(idx)


@DETERMINISTIC
@given(
    st.lists(
        st.datetimes(
            min_value=pd.Timestamp("2000-01-01").to_pydatetime(),
            max_value=pd.Timestamp("2050-01-01").to_pydatetime(),
        ),
        min_size=1,
        max_size=30,
    )
)
def test_normalize_timestamps_is_utc_idempotent_and_length_preserving(naive):
    idx = normalize_timestamps(naive, assume_tz="UTC")
    assert len(idx) == len(naive) and str(idx.tz) == "UTC"
    assert normalize_timestamps(idx).equals(idx)


@DETERMINISTIC
@given(st.lists(st.sampled_from([0.0, 1.0, 2.0, np.nan, np.inf]), max_size=40), st.integers(2, 5))
def test_stale_mask_matches_brute_force(data, min_run):
    expected = [False] * len(data)
    i = 0
    while i < len(data):
        j = i
        if np.isfinite(data[i]):
            while j + 1 < len(data) and np.isfinite(data[j + 1]) and data[j + 1] == data[i]:
                j += 1
            if j - i + 1 >= min_run:
                expected[i : j + 1] = [True] * (j - i + 1)
        i = j + 1
    assert stale_mask(data, min_run).tolist() == expected


@DETERMINISTIC
@given(st.lists(st.one_of(st.floats(-100, 100), st.just(np.nan), st.just(np.inf)), max_size=40))
def test_counter_decrease_matches_brute_force(data):
    expected, last = [], None
    for v in data:
        finite = np.isfinite(v)
        expected.append(bool(finite and last is not None and v < last))
        if finite:
            last = v
    assert counter_decrease_mask(data).tolist() == expected


@DETERMINISTIC
@given(grid_series(max_slots=400))
def test_local_day_counts_are_bounded(series):
    days = local_day_completeness(series.index, STEP, "Europe/Stockholm")
    assert (days["present"] <= days["expected"]).all()
    assert (days["missing"] == days["expected"] - days["present"]).all()
    assert int(days["present"].sum()) == series.index.unique().size  # all on-grid here


@DETERMINISTIC
@given(
    unit=st.sampled_from(["W", "kW", "MWh", "kvar", "VA", "V", "A", "degC", "Hz"]),
    resolution=st.sampled_from([None, "15min", "1h", "D", "MS"]),
    aggregation=st.sampled_from(list(Aggregation)),
    label=st.sampled_from(list(IntervalLabel)),
    zone=st.sampled_from(["UTC", "Europe/Stockholm"]),
    description=st.text(max_size=20),
)
def test_table_schema_round_trip(unit, resolution, aggregation, label, zone, description):
    meta = MeasurementMetadata(
        name="value",
        unit=unit,
        resolution=resolution,
        aggregation=aggregation,
        interval_label=label,
        timezone=zone,
        description=description,
    )
    schema = json.loads(json.dumps(to_table_schema(meta, include_flag=True)))
    assert from_table_schema(schema) == meta


@DETERMINISTIC
@given(
    st.lists(st.one_of(st.floats(-100, 100), st.just(np.nan), st.just(np.inf)), max_size=40),
    st.floats(0.5, 50),
)
def test_jump_matches_brute_force(data, max_delta):
    expected, last = [], None
    for v in data:
        finite = np.isfinite(v)
        expected.append(bool(finite and last is not None and abs(v - last) > max_delta))
        if finite:
            last = v
    assert jump_mask(data, max_delta).tolist() == expected
