import json

import pytest

from energydata_kit import (
    MeasurementMetadata,
    ReportComparison,
    assess_frame,
    assess_quality,
    compare_reports,
    make_synthetic_series,
)


def report(**kwargs):
    defaults = {"periods": 96}
    return assess_quality(make_synthetic_series(**(defaults | kwargs)), freq="15min")


def test_identical_reports():
    a = report(drop=[3])
    result = compare_reports(a, a)
    assert isinstance(result, ReportComparison)
    assert result.same_data and not result.worse
    assert result.changes == {"": {}}


def test_fix_shows_deltas_resolved_gaps_and_is_not_worse():
    before = report(drop=[10, 11, 12], inf_at=[5])
    after = report(drop=[12])
    result = compare_reports(before, json.loads(after.to_json()))  # saved JSON works too
    changes = result.changes[""]
    assert not result.same_data and not result.worse
    assert changes["counts"]["n_missing_intervals"] == {"before": 3, "after": 1, "delta": -2}
    assert changes["flag_counts"]["NON_FINITE"] == {"before": 1, "after": 0, "delta": -1}
    assert changes["gaps"]["resolved"][0]["missing_count"] == 3
    assert changes["gaps"]["new"][0]["missing_count"] == 1  # the remaining, smaller gap
    assert "parameters" not in changes


def test_worse_when_more_flags_or_missing():
    good = report()
    assert compare_reports(good, report(inf_at=[7])).worse
    assert compare_reports(good, report(drop=[4])).worse
    assert not compare_reports(report(drop=[4]), good).worse


def test_parameters_and_metadata_issues():
    series = make_synthetic_series(periods=8)
    meta = MeasurementMetadata(name="synthetic_power", unit="kW", resolution="15min", aggregation="sum")
    a = assess_quality(series, freq="15min")
    b = assess_quality(series, metadata=meta, bounds=(0, None))
    changes = compare_reports(a, b).changes[""]
    assert changes["parameters"]["bounds"] == {"before": None, "after": [0, None]}
    assert changes["metadata_issues"] == {"resolved": [], "new": ["SUM_OF_POWER"]}
    assert changes["metadata"]["unit"] == {"before": None, "after": "kW"}
    assert compare_reports(a, b).same_data


def test_frame_reports_by_column():
    import pandas as pd

    p = make_synthetic_series(periods=6, name="p")
    before = assess_frame(pd.DataFrame({"p": p, "q": p * 2}), freq="15min")
    p2 = p.copy()
    p2.iloc[2] = float("inf")
    after = assess_frame(pd.DataFrame({"p": p2, "r": p}), freq="15min")
    result = compare_reports(before, after)
    assert result.columns_added == ["r"] and result.columns_removed == ["q"]
    assert list(result.changes) == ["p"]
    assert result.changes["p"]["flag_counts"]["NON_FINITE"]["delta"] == 1
    assert result.worse


def test_deterministic_json():
    a, b = report(drop=[1]), report(drop=[2])
    assert compare_reports(a, b).to_json() == compare_reports(a, b).to_json()


def test_rejects_mismatched_inputs():
    single = report()
    frame = assess_frame(make_synthetic_series(periods=4).to_frame(), freq="15min")
    with pytest.raises(ValueError, match="single-series"):
        compare_reports(single, frame)
    old = single.to_dict() | {"schema_version": "0"}
    with pytest.raises(ValueError, match="schema_version '0'"):
        compare_reports(old, single)
    with pytest.raises(TypeError):
        compare_reports("report.json", single)  # type: ignore[arg-type]
