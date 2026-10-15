import pandas as pd
import pytest

from energydata_kit import (
    Aggregation,
    IntervalLabel,
    MeasurementMetadata,
    UnitError,
    units_compatible,
    validate_unit,
)


@pytest.mark.parametrize(
    "unit", ["W", "kW", "MW", "kWh", "MWh", "var", "kvar", "VA", "kV", "A", "Hz", "degC", "W/m^2"]
)
def test_common_energy_units(unit):
    assert validate_unit(unit) == unit


@pytest.mark.parametrize("unit", ["", "  ", "kilowombat", "kW kilowombat"])
def test_invalid_units(unit):
    with pytest.raises(UnitError):
        validate_unit(unit)


def test_units_compatible():
    assert units_compatible("kW", "MW")
    assert units_compatible("kvar", "kVA")
    assert not units_compatible("kW", "kWh")


def test_metadata_roundtrip():
    meta = MeasurementMetadata(
        name="import_energy", unit="kWh", resolution="15min", aggregation="sum", interval_label="end"
    )
    assert meta.aggregation is Aggregation.SUM
    assert meta.interval_label is IntervalLabel.END
    assert meta.resolution_timedelta == pd.Timedelta("15min")
    data = meta.to_dict()
    assert data["aggregation"] == "sum"
    assert MeasurementMetadata.from_dict(data) == meta


@pytest.mark.parametrize(
    "kwargs",
    [
        {"name": "", "unit": "kW"},
        {"name": "p", "unit": "nope"},
        {"name": "p", "unit": "kW", "resolution": "0min"},
        {"name": "p", "unit": "kW", "resolution": "-1MS"},
        {"name": "p", "unit": "kW", "resolution": "not-a-freq"},
        {"name": "p", "unit": "kW", "aggregation": "median"},
        {"name": "p", "unit": "kW", "interval_label": "middle"},
        {"name": "p", "unit": "kW", "timezone": "Mars/Olympus"},
    ],
)
def test_metadata_validation(kwargs):
    with pytest.raises(ValueError):
        MeasurementMetadata(**kwargs)


@pytest.mark.parametrize("resolution", ["15min", "1h", "D", "W-MON", "MS"])
def test_fixed_and_calendar_resolutions_accepted(resolution):
    assert MeasurementMetadata(name="p", unit="kW", resolution=resolution).resolution == resolution


def test_resolution_timedelta_rejects_calendar_steps():
    with pytest.raises(ValueError, match="tz="):
        _ = MeasurementMetadata(name="p", unit="kWh", resolution="MS").resolution_timedelta
