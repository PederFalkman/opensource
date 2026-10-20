import json
from pathlib import Path

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
    # The gap shrank from three intervals to one: one changed pair, not resolved plus new.
    assert changes["gaps"]["resolved"] == [] and changes["gaps"]["new"] == []
    [pair] = changes["gaps"]["changed"]
    assert (pair["before"]["missing_count"], pair["after"]["missing_count"]) == (3, 1)
    assert pair["after"]["end"] == pair["before"]["end"]
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
    saved_comparison = json.loads(compare_reports(a, b).to_json())  # carries a schema_version too
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


GOLDEN = Path(__file__).parent / "golden"


@pytest.mark.parametrize("name", ["single.json", "frame.json", "counter_local_day.json"])
def test_schema_1_reports_compare_with_schema_2_reports(name):
    # A 0.1.0 report (schema 1) against the same data reported by this version (schema 2):
    # nothing changed, so nothing is listed. In particular the new COUNTER_ROLLOVER count is
    # not reported as appearing, and the new parameters are not reported as changed (OSS-104).
    old = json.loads((GOLDEN / "schema1" / name).read_text(encoding="utf-8"))
    new = json.loads((GOLDEN / name).read_text(encoding="utf-8"))
    assert old["schema_version"] == "1" and new["schema_version"] == "2"
    for before, after in ((old, new), (new, old), (old, old)):
        result = compare_reports(before, after)
        assert result.schema_version == "2"
        assert all(changes == {} for changes in result.changes.values()), result.changes


def test_schema_1_report_against_a_changed_schema_2_report():
    old = json.loads((GOLDEN / "schema1" / "single.json").read_text(encoding="utf-8"))
    new = json.loads((GOLDEN / "single.json").read_text(encoding="utf-8"))
    new["flag_counts"]["JUMP"] += 1
    new["flag_counts"]["COUNTER_ROLLOVER"] = 3  # one side only: not compared
    changes = compare_reports(old, new).changes[""]
    assert changes["flag_counts"] == {"JUMP": {"before": 0, "after": 1, "delta": 1}}


def gaps(before_drop, after_drop):
    return compare_reports(report(drop=before_drop), report(drop=after_drop)).changes[""]["gaps"]


def counts(section):
    return [len(section[k]) for k in ("resolved", "new", "changed")]


def test_gaps_that_do_not_overlap_are_resolved_and_new():
    # Overlap matching (P-10): gaps are compared as intervals of missing timestamps, both
    # ends included. Disjoint gaps, even adjacent ones, are not the same gap.
    assert counts(gaps([3], [5])) == [1, 1, 0]
    assert counts(gaps([3], [4])) == [1, 1, 0]


def test_a_gap_that_grew_shrank_or_moved_is_changed():
    grew = gaps([10], [9, 10, 11])
    assert counts(grew) == [0, 0, 1]
    assert [grew["changed"][0][side]["missing_count"] for side in ("before", "after")] == [1, 3]
    assert counts(gaps([9, 10, 11], [10])) == [0, 0, 1]
    assert counts(gaps([9, 10], [10, 11])) == [0, 0, 1]


def test_split_and_merged_gaps_list_each_overlapping_pair():
    split = gaps([10, 11, 12, 13, 14], [10, 11, 13, 14])
    assert counts(split) == [0, 0, 2]
    assert len({json.dumps(pair["before"]) for pair in split["changed"]}) == 1  # one gap became two
    merged = gaps([10, 11, 13, 14], [10, 11, 12, 13, 14])
    assert counts(merged) == [0, 0, 2]
    assert len({json.dumps(pair["after"]) for pair in merged["changed"]}) == 1
    # Pairs are listed in time order, by the before gap and then the after gap.
    starts = [(p["before"]["start"], p["after"]["start"]) for p in split["changed"] + merged["changed"]]
    assert starts[:2] == sorted(starts[:2]) and starts[2:] == sorted(starts[2:])


def test_exact_overlapping_and_disjoint_gaps_together():
    section = gaps([2, 10, 11, 30, 50, 52], [2, 11, 12, 40, 50, 51, 52])
    # 2: unchanged, not listed. 10-11 -> 11-12: changed. 30: resolved. 40: new.
    # 50 and 52 -> 50-52: two pairs (merged).
    assert counts(section) == [1, 1, 3]
    assert section["resolved"][0]["missing_count"] == 1 and section["new"][0]["missing_count"] == 1
    listed = [g["start"] for g in section["resolved"] + section["new"]]
    listed += [p[side]["start"] for p in section["changed"] for side in ("before", "after")]
    assert report(drop=[2]).gaps[0].start.isoformat() not in listed


def test_overlap_matching_does_not_change_worse():
    # worse is still decided by counts: more missing intervals is worse whatever the matching.
    assert compare_reports(report(drop=[10]), report(drop=[9, 10, 11])).worse
    assert not compare_reports(report(drop=[9, 10, 11]), report(drop=[10])).worse


def test_only_listed_gaps_are_matched():
    def capped(drop):
        return assess_quality(make_synthetic_series(periods=96, drop=drop), freq="15min", max_listed=1)

    # Only the first gap is listed on each side, and it is the same, so no gap is listed as
    # changed although the unlisted third gap moved; the counts still show the data changed.
    changes = compare_reports(capped([10, 20, 30]), capped([10, 20, 31])).changes[""]
    assert "gaps" not in changes and changes["fingerprint"]
    section = compare_reports(capped([10, 20, 30]), capped([9, 10, 20, 30])).changes[""]["gaps"]
    assert counts(section) == [0, 0, 1] and section["lists_truncated"]
