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


def test_null_truncated_is_read_as_not_truncated():
    # "truncated": null passes the input check but crashed with AttributeError when gaps differed.
    before = assess_quality(make_synthetic_series(periods=8), freq="15min").to_dict()
    after = assess_quality(make_synthetic_series(periods=8, drop=[3]), freq="15min").to_dict()
    after["truncated"] = None
    assert compare_reports(before, after).changes[""]["gaps"]["lists_truncated"] is False


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


def test_rejects_a_comparison_or_a_hand_edited_report():
    a, b = report(drop=[3]), report()
    saved_comparison = json.loads(compare_reports(a, b).to_json())  # also schema "1"
    with pytest.raises(ValueError, match="before is not a quality report: fingerprint"):
        compare_reports(saved_comparison, b)

    edited = a.to_dict()
    del edited["gaps"][0]["end"]
    with pytest.raises(ValueError, match="after is not a quality report: gaps"):
        compare_reports(a, edited)

    edited = a.to_dict() | {"flag_counts": "many"}
    with pytest.raises(ValueError, match="flag_counts"):
        compare_reports(edited, a)


def test_rejects_a_frame_report_with_inconsistent_columns():
    frame = assess_frame(make_synthetic_series(periods=4).to_frame("p"), freq="15min").to_dict()
    renamed = frame | {"column_order": ["p", "q"]}
    with pytest.raises(ValueError, match="column_order"):
        compare_reports(frame, renamed)
    broken = json.loads(json.dumps(frame))
    broken["columns"]["p"]["metadata_issues"] = [{"message": "no code"}]
    with pytest.raises(ValueError, match=r"columns\.p\.metadata_issues"):
        compare_reports(broken, frame)


def test_known_outages_appear_in_the_comparison():
    s = make_synthetic_series(periods=96, drop=[10, 11])
    before = assess_quality(s, freq="15min")
    after = assess_quality(s, freq="15min", known_outages=[("2024-01-01T02:30Z", "2024-01-01T02:45Z")])
    counts = compare_reports(before, after).changes[""]["counts"]
    assert counts["n_missing_explained"] == {"before": 0, "after": 2, "delta": 2}
    assert counts["completeness_excluding_outages"] == {"before": None, "after": 1.0}
    assert not compare_reports(before, after).worse
