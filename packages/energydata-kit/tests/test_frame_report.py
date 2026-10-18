import json

import numpy as np
import pandas as pd
import pytest

from energydata_kit import (
    FLAG_COLUMN,
    FrameQualityReport,
    MeasurementMetadata,
    assess_frame,
    assess_quality,
    flag_column,
    flag_frame,
    flag_series,
    make_synthetic_series,
)
from energydata_kit.frame_report import COLUMN_OPTIONS, FLAG_OPTIONS, TIMESTAMP_FIELDS


def meter_frame() -> pd.DataFrame:
    power = make_synthetic_series(periods=8, drop=[3], inf_at=[5], name="power_kw")
    energy = pd.Series([10.0, 10.5, 11.0, 11.5, 2.0, 2.5, 3.0], index=power.index, name="energy_kwh")
    return pd.DataFrame({"power_kw": power, "energy_kwh": energy})


def test_each_column_report_equals_assess_quality():
    frame = meter_frame()
    report = assess_frame(frame, freq="15min", per_column={"energy_kwh": {"cumulative": True}})
    assert isinstance(report, FrameQualityReport)
    assert list(report.columns) == ["power_kw", "energy_kwh"]
    alone = assess_quality(frame["power_kw"], freq="15min")
    assert report.columns["power_kw"].to_json() == alone.to_json()
    energy = assess_quality(frame["energy_kwh"], freq="15min", cumulative=True)
    assert report.columns["energy_kwh"].to_json() == energy.to_json()
    assert report.summary["energy_kwh"]["n_flagged_rows"] == 1  # the counter reset
    assert report.summary["power_kw"]["n_missing_intervals"] == 1


def test_shared_options_metadata_and_column_selection():
    frame = meter_frame()
    meta = {
        "power_kw": MeasurementMetadata(name="power_kw", unit="kW", resolution="15min", aggregation="sum")
    }
    report = assess_frame(frame, columns=["power_kw"], metadata=meta, bounds=(0, None))
    data = json.loads(report.to_json())
    assert data["column_order"] == ["power_kw"]
    column = data["columns"]["power_kw"]
    assert column["metadata"]["unit"] == "kW" and column["parameters"]["bounds"] == [0, None]
    assert [i["code"] for i in column["metadata_issues"]] == ["SUM_OF_POWER"]
    assert data["summary"]["power_kw"]["n_metadata_issues"] == 1


def test_deterministic_and_fingerprint_tracks_columns():
    frame = meter_frame()
    a = assess_frame(frame, freq="15min")
    assert a.to_json() == assess_frame(frame.copy(), freq="15min").to_json()
    reordered = assess_frame(frame, columns=["energy_kwh", "power_kw"], freq="15min")
    assert reordered.fingerprint != a.fingerprint  # column order is part of the data
    changed = frame.copy()
    changed.iloc[0, 1] = 99.0
    assert assess_frame(changed, freq="15min").fingerprint != a.fingerprint


def test_frame_is_not_modified():
    frame = meter_frame()
    before = frame.copy(deep=True)
    assess_frame(frame, freq="15min", stale_min_run=2, jump_max_delta=1.0)
    pd.testing.assert_frame_equal(frame, before)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"columns": []}, "no columns"),
        ({"columns": ["nope"]}, "not in frame"),
        ({"columns": ["power_kw", "power_kw"]}, "unique"),
        ({"metadata": {"nope": MeasurementMetadata(name="nope", unit="kW")}}, "not assessed"),
        ({"metadata": {"power_kw": MeasurementMetadata(name="other", unit="kW")}}, "is named 'other'"),
        ({"per_column": {"power_kw": {"freq": "1h"}}}, "unsupported options"),
        ({"per_column": {"nope": {"cumulative": True}}}, "not assessed"),
        ({"per_column": {"power_kw": {"counter_tolerance": 1.0}}}, "requires cumulative"),
    ],
)
def test_invalid_arguments(kwargs, message):
    with pytest.raises(ValueError, match=message):
        assess_frame(meter_frame(), **kwargs)


def test_non_string_column_names_rejected():
    frame = pd.DataFrame(
        {0: np.arange(3.0)}, index=pd.date_range("2024-01-01", periods=3, freq="h", tz="UTC")
    )
    with pytest.raises(ValueError, match="strings"):
        assess_frame(frame)


def test_column_options_match_assess_quality_parameters():
    import inspect

    params = set(inspect.signature(assess_quality).parameters)
    assert params - {"series", "freq", "origin", "tz", "known_outages", "max_listed"} == COLUMN_OPTIONS


def test_flag_frame_columns_equal_flag_series():
    frame = meter_frame()
    out = flag_frame(
        frame, freq="15min", insert_missing=True, per_column={"energy_kwh": {"cumulative": True}}
    )
    assert list(out.columns) == ["power_kw", "quality_flag_power_kw", "energy_kwh", "quality_flag_energy_kwh"]
    for name, options in (("power_kw", {}), ("energy_kwh", {"cumulative": True})):
        alone = flag_series(frame[name], freq="15min", insert_missing=True, **options)
        assert out.index.equals(alone.index)
        assert out[flag_column(name)].tolist() == alone[FLAG_COLUMN].tolist()
        np.testing.assert_array_equal(out[name].to_numpy(dtype=float), alone["value"].to_numpy(dtype=float))
    assert len(out) == len(frame) + 1  # one inserted row shared by both columns


def test_flag_frame_leaves_input_alone_and_validates():
    frame = meter_frame()
    before = frame.copy(deep=True)
    flag_frame(frame, freq="15min", stale_min_run=2)
    pd.testing.assert_frame_equal(frame, before)
    with pytest.raises(ValueError, match="unsupported options"):
        flag_frame(frame, per_column={"power_kw": {"metadata": None}})
    clash = pd.DataFrame({"x": [1.0], "quality_flag_x": [0]}, index=frame.index[:1])
    with pytest.raises(ValueError, match="already used"):
        flag_frame(clash)
    assert flag_frame(frame, columns=["energy_kwh"]).columns.tolist() == [
        "energy_kwh",
        "quality_flag_energy_kwh",
    ]


def test_flag_options_are_the_column_options_without_metadata():
    assert COLUMN_OPTIONS - {"metadata"} == FLAG_OPTIONS


def test_per_column_metadata_must_match_its_column():
    frame = pd.DataFrame({"a": [1.0, 2.0]}, index=pd.date_range("2024-01-01", periods=2, freq="h", tz="UTC"))
    other = MeasurementMetadata("zzz", "kW")
    with pytest.raises(ValueError, match="per_column\\['a'\\] metadata is named 'zzz'"):
        assess_frame(frame, per_column={"a": {"metadata": other}})


def test_shared_timestamp_section():
    frame = meter_frame()
    report = assess_frame(frame, freq="15min", per_column={"energy_kwh": {"cumulative": True}})
    shared = report.timestamps
    assert shared is not None and report.to_dict()["timestamps"] == shared
    # The same facts every column reports: written once, columns unchanged.
    for column in report.columns.values():
        data = column.to_dict()
        assert {key: data[key] for key in TIMESTAMP_FIELDS} == {key: shared[key] for key in TIMESTAMP_FIELDS}
    assert shared["n_rows"] == 7 and shared["n_missing_intervals"] == 1
    assert shared["gaps"] == [
        {"start": "2024-01-01T00:45:00+00:00", "end": "2024-01-01T00:45:00+00:00", "missing_count": 1}
    ]
    assert shared["truncated"] == {"gaps": False, "duplicate_timestamps": False}


def test_known_outages_reach_every_column():
    # A generator was used up by the first column, so later columns had no outages.
    frame = meter_frame()
    outages = (pair for pair in [("2024-01-01T00:30Z", "2024-01-01T01:00Z")])
    report = assess_frame(frame, freq="15min", known_outages=outages)
    assert [r.n_missing_explained for r in report.columns.values()] == [1, 1]
    assert report.timestamps is not None and report.timestamps["n_missing_explained"] == 1
    single = assess_quality(
        frame["power_kw"], freq="15min", known_outages=[("2024-01-01T00:30Z", "2024-01-01T01:00Z")]
    )
    assert report.columns["power_kw"].to_json() == single.to_json()


def test_no_shared_timestamp_section_when_steps_differ():
    # Without --freq each column takes its step from its metadata; 15 and 30 minutes disagree.
    frame = meter_frame()
    metadata = {
        "power_kw": MeasurementMetadata("power_kw", "kW", resolution="15min"),
        "energy_kwh": MeasurementMetadata("energy_kwh", "kWh", resolution="30min"),
    }
    report = assess_frame(frame, metadata=metadata)
    assert report.timestamps is None and report.to_dict()["timestamps"] is None
    # Without any step, the index facts still agree (no grid, same rows and duplicates).
    assert assess_frame(frame).timestamps["expected_resolution"] is None
