"""Byte-for-byte golden outputs, so reports stay identical across pandas, numpy
and Python versions (CI runs this on each supported version and on the lowest
dependency versions).

The inputs are synthetic and fixed. ``package_version`` is masked so a version
bump alone does not fail the test. After an intended change to report
content, regenerate with ``EDK_UPDATE_GOLDEN=1 pytest tests/test_golden.py``,
review the diff and record the change in the CHANGELOG.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import energydata_kit as ek

GOLDEN = Path(__file__).parent / "golden"
_VERSION = re.compile(r'"package_version": "[^"]*"')


def _sorted(series: pd.Series) -> pd.Series:
    return series.sort_index(kind="stable")


def outputs() -> dict[str, str]:
    tz = "Europe/Stockholm"
    s = ek.make_synthetic_series(
        periods=192, drop=[5, 6, 100], duplicate=[40], nan_at=[70], inf_at=[90], start="2024-03-30T00:00:00Z"
    )
    s.iloc[120:126] = s.iloc[120]  # a stale run
    s = _sorted(s)
    meta = ek.MeasurementMetadata(
        "synthetic_power", "kW", resolution="15min", aggregation="mean", timezone=tz
    )
    counter = pd.Series(
        np.cumsum(np.arange(72, dtype=float)),
        index=pd.date_range("2024-10-25 22:00", periods=72, freq="h", tz="UTC"),  # local midnight, DST day
        name="kwh",
    )
    counter.iloc[30] = 1.0  # a counter decrease
    frame = pd.DataFrame({"a": s.to_numpy()[:150], "b": np.linspace(0, 1, 150)}, index=s.index[:150])
    frame = frame[~frame.index.duplicated()]
    frame_report = ek.assess_frame(frame, freq="15min", per_column={"a": {"bounds": (0, 110)}})
    return {
        "single.json": ek.assess_quality(
            s, metadata=meta, bounds=(0, 110), stale_min_run=4, jump_max_delta=15
        ).to_json(),
        "counter_local_day.json": ek.assess_quality(counter, freq="D", tz=tz, cumulative=True).to_json(),
        "frame.json": frame_report.to_json(),
        "compare.json": ek.compare_reports(
            frame_report, ek.assess_frame(frame.iloc[::2], freq="15min")
        ).to_json(),
        "flags.csv": ek.flag_series(s, freq="15min", bounds=(0, 110), insert_missing=True).to_csv(
            date_format="%Y-%m-%dT%H:%M:%S%z", lineterminator="\n"
        ),
        "fingerprints.json": json.dumps(
            [ek.fingerprint_series(x) for x in (s, counter, frame["b"], s.astype(object))], indent=2
        ),
    }


@pytest.mark.parametrize("name", sorted(outputs()))
def test_golden_output(name):
    actual = _VERSION.sub('"package_version": "*"', outputs()[name])
    path = GOLDEN / name
    if os.environ.get("EDK_UPDATE_GOLDEN"):
        path.write_text(actual, encoding="utf-8")
    assert actual == path.read_text(encoding="utf-8"), f"{name} changed; see the module docstring"
