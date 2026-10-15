import numpy as np
import pandas as pd
import pytest

from energydata_kit import make_synthetic_series


def test_deterministic():
    pd.testing.assert_series_equal(make_synthetic_series(seed=1), make_synthetic_series(seed=1))
    assert not make_synthetic_series(seed=1).equals(make_synthetic_series(seed=2))


def test_shape_and_index():
    s = make_synthetic_series(periods=24, freq="1h")
    assert len(s) == 24 and str(s.index.tz) == "UTC" and s.index.is_monotonic_increasing


def test_defects():
    s = make_synthetic_series(periods=10, drop=[0], duplicate=[5], nan_at=[2], inf_at=[3])
    assert len(s) == 10
    assert s.index.duplicated().sum() == 1
    assert s.isna().sum() == 1 and np.isinf(s).sum() == 1


def test_invalid_args():
    with pytest.raises(IndexError):
        make_synthetic_series(periods=4, drop=[4])
    with pytest.raises(ValueError):
        make_synthetic_series(start="2024-01-01")
    with pytest.raises(ValueError):
        make_synthetic_series(periods=-1)
