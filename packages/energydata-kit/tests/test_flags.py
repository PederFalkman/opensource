import numpy as np
import pandas as pd
import pytest

from energydata_kit import (
    FLAG_COLUMN,
    VALUE_COLUMN,
    QualityFlag,
    decode_flags,
    flag_series,
    make_synthetic_series,
    missing_value_mask,
    non_finite_mask,
    non_numeric_mask,
    out_of_bounds_mask,
)


def test_value_masks():
    values = pd.Series([1.0, np.nan, np.inf, -np.inf, None, "abc", "2.5", pd.NA], dtype=object)
    assert missing_value_mask(values).tolist() == [False, True, False, False, True, False, False, True]
    assert non_finite_mask(values).tolist() == [False, False, True, True, False, False, False, False]
    assert non_numeric_mask(values).tolist() == [False, False, False, False, False, True, False, False]


def test_nullable_dtype():
    values = pd.Series([1.0, None, 3.0], dtype="Float64")
    assert missing_value_mask(values).tolist() == [False, True, False]
    assert not non_numeric_mask(values).any()


def test_out_of_bounds():
    values = [-1.0, 0.0, 5.0, 11.0, np.nan, np.inf]
    assert out_of_bounds_mask(values, lower=0, upper=10).tolist() == [True, False, False, True, False, False]
    assert out_of_bounds_mask(values, lower=0).tolist() == [True, False, False, False, False, False]
    assert not out_of_bounds_mask(values).any()
    with pytest.raises(ValueError):
        out_of_bounds_mask(values, lower=10, upper=0)


def test_flag_series_is_non_destructive():
    s = make_synthetic_series(duplicate=[2], nan_at=[1], inf_at=[3])
    before = s.copy(deep=True)
    out = flag_series(s, freq="15min", bounds=(0, 110))
    pd.testing.assert_series_equal(s, before)
    assert out.index.equals(s.index)
    np.testing.assert_array_equal(out[VALUE_COLUMN].to_numpy(), s.to_numpy())
    assert out[FLAG_COLUMN].dtype == np.uint16


def test_flag_series_combines_bits():
    s = make_synthetic_series(periods=6, duplicate=[2], nan_at=[1], inf_at=[2])
    flags = flag_series(s, freq="15min")[FLAG_COLUMN].tolist()
    dup_inf = int(QualityFlag.DUPLICATE_TIMESTAMP | QualityFlag.NON_FINITE)
    assert flags == [0, int(QualityFlag.MISSING_VALUE), dup_inf, dup_inf, 0, 0, 0]


def test_off_grid_and_bounds_flags():
    idx = pd.DatetimeIndex(["2024-01-01T00:00Z", "2024-01-01T00:07Z", "2024-01-01T00:15Z"])
    out = flag_series(pd.Series([1.0, 2.0, 500.0], index=idx), freq="15min", bounds=(None, 100))
    assert out[FLAG_COLUMN].tolist() == [
        0,
        int(QualityFlag.OFF_GRID_TIMESTAMP),
        int(QualityFlag.OUT_OF_BOUNDS),
    ]


def test_insert_missing():
    s = make_synthetic_series(periods=8, drop=[3, 4])
    out = flag_series(s, freq="15min", insert_missing=True)
    assert len(out) == 8
    inserted = out[(out[FLAG_COLUMN] & int(QualityFlag.MISSING_INTERVAL)) != 0]
    assert list(inserted.index) == [pd.Timestamp("2024-01-01T00:45Z"), pd.Timestamp("2024-01-01T01:00Z")]
    assert inserted[VALUE_COLUMN].isna().all()
    original = out[out[FLAG_COLUMN] == 0]
    np.testing.assert_array_equal(original[VALUE_COLUMN].to_numpy(), s.to_numpy())


def test_insert_missing_requirements():
    s = make_synthetic_series(periods=4)
    with pytest.raises(ValueError, match="requires freq"):
        flag_series(s, insert_missing=True)
    with pytest.raises(ValueError, match="sorted"):
        flag_series(s.iloc[::-1], freq="15min", insert_missing=True)


def test_naive_index_rejected():
    s = pd.Series([1.0], index=pd.DatetimeIndex(["2024-01-01"]))
    with pytest.raises(ValueError, match="timezone-aware"):
        flag_series(s)


def test_decode_flags():
    assert decode_flags(0) == ["OK"]
    assert decode_flags(1 | 8) == ["MISSING_VALUE", "DUPLICATE_TIMESTAMP"]


def test_flag_values_are_stable():
    # Public contract: never renumber.
    assert {name: f.value for name, f in QualityFlag.__members__.items()} == {
        "OK": 0,
        "MISSING_VALUE": 1,
        "NON_FINITE": 2,
        "NON_NUMERIC": 4,
        "DUPLICATE_TIMESTAMP": 8,
        "OFF_GRID_TIMESTAMP": 16,
        "OUT_OF_BOUNDS": 32,
        "MISSING_INTERVAL": 64,
        "STALE_VALUE": 128,
        "COUNTER_DECREASE": 256,
        "JUMP": 512,
    }
