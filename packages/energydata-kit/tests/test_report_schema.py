"""The shipped JSON Schema (``energydata_kit/report_schema.json``) matches real reports.

Every kind of report the package writes must validate, and reports with a
wrong type, an unknown field or another schema version must not. Needs the
``jsonschema`` dev dependency; skipped without it (e.g. the wheel test).
"""

import json
from importlib import resources
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import energydata_kit as ek

jsonschema = pytest.importorskip("jsonschema")

GOLDEN = Path(__file__).parent / "golden"
SCHEMA = json.loads(
    resources.files("energydata_kit").joinpath("report_schema.json").read_text(encoding="utf-8")
)
VALIDATOR = jsonschema.Draft202012Validator(SCHEMA)


def _errors(data):
    return [e.message for e in VALIDATOR.iter_errors(data)]


def test_schema_is_valid_and_describes_schema_1():
    jsonschema.Draft202012Validator.check_schema(SCHEMA)
    assert ek.QualityReport.__dataclass_fields__["schema_version"].default == "1"
    assert SCHEMA["$id"].endswith("report-schema-1.json")


@pytest.mark.parametrize("name", ["single.json", "counter_local_day.json", "frame.json", "compare.json"])
def test_golden_reports_validate(name):
    assert _errors(json.loads((GOLDEN / name).read_text(encoding="utf-8"))) == []


def _variants():
    s = ek.make_synthetic_series(periods=48, drop=[5, 6], nan_at=[3], inf_at=[9], duplicate=[20])
    meta = ek.MeasurementMetadata("p", "kW", resolution="15min", aggregation="sum")  # a metadata issue
    daily = pd.Series(1.0, index=pd.date_range("2024-03-28", periods=6, freq="D", tz="Europe/Stockholm"))
    frame = pd.DataFrame({"a": s.to_numpy(), "b": np.linspace(0, 1, len(s))}, index=s.index)
    frame = frame[~frame.index.duplicated()]
    reports = {
        "no step": ek.assess_quality(s),
        "empty": ek.assess_quality(s.iloc[:0], freq="15min"),
        "metadata": ek.assess_quality(s, metadata=meta, bounds=(0, None), max_listed=1),
        "every check": ek.assess_quality(
            s,
            freq="15min",
            bounds=(np.float64(0), 50),
            stale_min_run=3,
            stale_exclude=[0.0],
            cumulative=True,
            counter_tolerance=0.1,
            jump_max_delta=np.float32(5),
        ),
        "calendar": ek.assess_quality(daily.tz_convert("UTC"), freq="D", tz="Europe/Stockholm"),
        "step longer than a day": ek.assess_quality(s, freq="2D"),
        "known outages": ek.assess_quality(
            s, freq="15min", known_outages=[("2024-01-01T01:00Z", "2024-01-01T02:00Z")]
        ),
        "frame": ek.assess_frame(frame, freq="15min", per_column={"a": {"bounds": (0, 10)}}),
        "frame, no step": ek.assess_frame(frame),
    }
    reports["comparison"] = ek.compare_reports(reports["no step"], reports["metadata"])
    reports["frame comparison"] = ek.compare_reports(
        reports["frame"], ek.assess_frame(frame.rename(columns={"b": "c"}).iloc[::2], freq="15min")
    )
    return reports


@pytest.mark.parametrize("name", sorted(_variants()))
def test_generated_reports_validate(name):
    # Through JSON, as a consumer reads them.
    assert _errors(json.loads(_variants()[name].to_json())) == []


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d.update(schema_version="2"),
        lambda d: d.update(flag_counts="many"),
        lambda d: d.update(unexpected=1),
        lambda d: d.pop("fingerprint"),
        lambda d: d["gaps"].append({"start": "2024-01-01T00:00:00+00:00", "end": "x", "missing_count": 0}),
        lambda d: d.update(completeness=1.5),
        lambda d: d["parameters"].update(bounds=[0]),
    ],
)
def test_broken_reports_are_rejected(change):
    data = json.loads((GOLDEN / "single.json").read_text(encoding="utf-8"))
    change(data)
    assert _errors(data)


def test_comparison_and_frame_cannot_be_confused():
    comparison = json.loads((GOLDEN / "compare.json").read_text(encoding="utf-8"))
    frame = json.loads((GOLDEN / "frame.json").read_text(encoding="utf-8"))
    assert _errors(comparison | {"columns": frame["columns"]})
    assert _errors(frame | {"worse": False})
