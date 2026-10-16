import numpy as np
import pandas as pd
import pytest

from energydata_kit.timestamps import on_index, utc_ns


@pytest.mark.parametrize("unit", ["s", "ms", "us", "ns"])
@pytest.mark.parametrize("tz", ["UTC", "Europe/Stockholm", None])
def test_utc_ns_matches_as_unit_ns(unit, tz):
    idx = pd.date_range("2024-03-30", periods=200, freq="17min", tz=tz).as_unit(unit)
    expected = np.asarray(idx.as_unit("ns").to_numpy(dtype="datetime64[ns]")).view("i8")
    np.testing.assert_array_equal(utc_ns(idx), expected)


def test_utc_ns_out_of_range_raises():
    far = pd.DatetimeIndex(np.array(["2500-01-01"], dtype="datetime64[s]")).tz_localize("UTC")
    assert far.unit == "s"
    with pytest.raises((OverflowError, pd.errors.OutOfBoundsDatetime)):
        utc_ns(far)


def test_on_index_matches_isin():
    rng = np.random.default_rng(0)
    base = pd.date_range("2024-01-01", periods=500, freq="15min", tz="UTC")
    index = base[rng.permutation(500)[:300]].append(base[:5])  # unsorted, with duplicates
    index = index.tz_convert("Europe/Stockholm").as_unit("us")
    grid = pd.date_range("2023-12-31T23:00Z", periods=600, freq="15min")
    np.testing.assert_array_equal(on_index(grid, index), grid.isin(index.tz_convert("UTC").as_unit("ns")))
    assert not on_index(grid, pd.DatetimeIndex([], tz="UTC")).any()
    assert on_index(pd.DatetimeIndex([], tz="UTC"), index).size == 0
