import json

import numpy as np
import pandas as pd
import pytest

from energydata_kit import (
    MeasurementMetadata,
    __version__,
    assess_quality,
    fingerprint_series,
    make_synthetic_series,
)


def defective():
    return make_synthetic_series(drop=[5, 6, 7, 40], duplicate=[10], nan_at=[3], inf_at=[20])


def test_report_contents():
    r = assess_quality(defective(), freq="15min", bounds=(0, 200))
    assert r.n_rows == 93
    assert r.n_expected_intervals == 96
    assert r.completeness == round(92 / 96, 6)
    assert r.n_gaps == 2 and r.n_missing_intervals == 4
    assert r.n_duplicate_timestamps == 1
    assert r.flag_counts["MISSING_VALUE"] == 1
    assert r.flag_counts["NON_FINITE"] == 1
    assert r.flag_counts["DUPLICATE_TIMESTAMP"] == 2
    assert r.n_flagged_rows == 4
    assert r.package_version == __version__


def test_report_json_is_deterministic():
    a = assess_quality(defective(), freq="15min").to_json()
    b = assess_quality(defective(), freq="15min").to_json()
    assert a == b
    data = json.loads(a)
    assert data["schema_version"] == "1"
    assert data["gaps"][0] == {
        "start": "2024-01-01T01:15:00+00:00",
        "end": "2024-01-01T01:45:00+00:00",
        "missing_count": 3,
    }


def test_resolution_from_metadata_and_no_silent_guess():
    meta = MeasurementMetadata(name="p", unit="kW", resolution="15min")
    assert assess_quality(defective(), metadata=meta).n_gaps == 2
    r = assess_quality(defective())
    assert r.expected_resolution is None and r.gaps == [] and r.completeness is None
    assert r.inferred_resolution == "P0DT0H15M0S"


def test_truncation():
    r = assess_quality(defective(), freq="15min", max_listed=1)
    assert len(r.gaps) == 1 and r.n_gaps == 2
    assert r.truncated == {"gaps": True, "duplicate_timestamps": False, "incomplete_local_days": False}
    with pytest.raises(ValueError):
        assess_quality(defective(), max_listed=-1)


def test_fingerprint_independent_of_datetime_unit_and_tz():
    s = make_synthetic_series(periods=10)
    other_unit = s.copy()
    other_unit.index = other_unit.index.as_unit("us")
    other_tz = s.copy()
    other_tz.index = other_tz.index.tz_convert("Europe/Stockholm")
    assert fingerprint_series(s) == fingerprint_series(other_unit) == fingerprint_series(other_tz)


def test_fingerprint_sensitive_to_data():
    s = make_synthetic_series(periods=10)
    changed = s.copy()
    changed.iloc[0] += 1e-9
    assert fingerprint_series(s) != fingerprint_series(changed)
    assert fingerprint_series(s) != fingerprint_series(s.rename("other"))
    text = pd.Series(["a", "b"], index=s.index[:2])
    assert fingerprint_series(text) != fingerprint_series(pd.Series(["a", "c"], index=s.index[:2]))


def test_fingerprint_canonical_nan():
    s = make_synthetic_series(periods=3)
    a, b = s.copy(), s.copy()
    a.iloc[1] = np.nan
    b.iloc[1] = -np.nan
    assert fingerprint_series(a) == fingerprint_series(b)


def test_empty_series():
    r = assess_quality(pd.Series([], index=pd.DatetimeIndex([], tz="UTC"), dtype=float), freq="1h")
    assert r.n_rows == 0 and r.first_timestamp is None and r.completeness is None


def test_single_row_and_all_missing_values():
    idx = pd.date_range("2026-01-01", periods=4, freq="15min", tz="UTC")
    one = assess_quality(pd.Series([1.0], index=idx[:1]), freq="15min")
    assert (one.n_rows, one.completeness, one.n_flagged_rows) == (1, 1.0, 0)
    assert assess_quality(pd.Series([1.0], index=idx[:1])).completeness is None  # no step, no guess
    # Completeness counts timestamps; missing values are flagged separately.
    nan = assess_quality(pd.Series([np.nan] * 4, index=idx), freq="15min")
    assert nan.completeness == 1.0
    assert nan.flag_counts["MISSING_VALUE"] == 4 and nan.n_flagged_rows == 4


def test_no_grid_point_in_span_gives_no_completeness():
    s = pd.Series([1.0, 2.0], index=pd.DatetimeIndex(["2024-01-01 10:00", "2024-01-01 11:00"], tz="UTC"))
    r = assess_quality(s, freq="1D", origin=pd.Timestamp("2024-01-01", tz="UTC"))
    assert r.n_expected_intervals == 0 and r.completeness is None


def test_numpy_scalar_options_give_json_parameters():
    s = defective()
    r = assess_quality(
        s,
        freq="15min",
        bounds=(np.float64(0), np.int64(200)),
        stale_min_run=np.int64(3),
        stale_atol=np.float64(0.0),
        jump_max_delta=np.float32(50),
        max_listed=np.int64(5),
    )
    params = json.loads(r.to_json())["parameters"]
    assert params["bounds"] == [0.0, 200] and params["stale_min_run"] == 3
    assert params["jump_max_delta"] == 50.0 and params["max_listed"] == 5


def test_max_listed_must_be_an_integer():
    with pytest.raises(TypeError):
        assess_quality(defective(), max_listed=1.5)


def test_nat_in_index_is_rejected():
    s = pd.Series([1.0, 2.0], index=pd.DatetimeIndex([pd.Timestamp("2024-01-01T00:00Z"), pd.NaT]))
    with pytest.raises(ValueError, match="NaT"):
        assess_quality(s, freq="15min")


def test_known_outages_explain_missing_intervals():
    s = make_synthetic_series(periods=96, drop=[10, 11, 12, 40, 41])  # gaps at 02:30-03:00 and 10:00-10:15
    outage = ("2024-01-01T02:00Z", "2024-01-01T03:59Z")  # grid 02:00-03:45, 8 points, 3 of them missing
    r = assess_quality(s, freq="15min", known_outages=[outage])
    # Gaps, totals, completeness and flags are unchanged: an outage explains a gap, it does not hide it.
    plain = assess_quality(s, freq="15min")
    assert (r.n_gaps, r.n_missing_intervals, r.completeness) == (
        plain.n_gaps,
        plain.n_missing_intervals,
        plain.completeness,
    )
    assert r.flag_counts == plain.flag_counts and r.fingerprint == plain.fingerprint
    assert r.n_missing_explained == 3
    assert r.completeness_excluding_outages == round(86 / 88, 6)
    assert r.parameters["known_outages"] == [["2024-01-01T02:00:00+00:00", "2024-01-01T03:59:00+00:00"]]
    # Without outages: nothing explained, nothing excluded; without a step: not computed.
    assert (plain.n_missing_explained, plain.completeness_excluding_outages) == (0, None)
    assert assess_quality(s, known_outages=[outage]).n_missing_explained is None
    # An outage covering the whole grid leaves nothing to measure.
    everything = assess_quality(s, freq="15min", known_outages=[("2023-01-01T00:00Z", "2025-01-01T00:00Z")])
    assert everything.n_missing_explained == 5 and everything.completeness_excluding_outages is None


@pytest.mark.parametrize(
    ("outages", "error"),
    [
        ([("2024-01-01T02:00", "2024-01-01T03:00")], "timezone-aware"),
        ([("2024-01-01T05:00Z", "2024-01-01T03:00Z")], "starts after it ends"),
        ([("2024-01-01T05:00Z",)], r"\(start, end\) pair"),
        ("2024-01-01T05:00Z", "list of"),
    ],
)
def test_known_outages_are_validated(outages, error):
    with pytest.raises((ValueError, TypeError), match=error):
        assess_quality(defective(), freq="15min", known_outages=outages)
