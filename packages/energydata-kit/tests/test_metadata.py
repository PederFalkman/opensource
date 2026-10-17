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


@pytest.mark.parametrize("unit", ["kilowatts?", "kW!", "kWh;", "kW#comment", "(kW"])
def test_units_with_stray_characters_are_rejected(unit):
    # Pint drops some trailing characters ("kW?" parses as kW) or raises a TokenError.
    with pytest.raises(UnitError):
        validate_unit(unit)


@pytest.mark.parametrize("unit", ["kW", "m^3/h", "W/m**2", "Wh/(m^2)", "°C", "%", "µs", "kW*h"])
def test_unit_expressions_still_accepted(unit):
    assert validate_unit(unit) == unit


def test_resolution_must_be_a_string():
    # A Timedelta would not survive JSON, and its string form differs between pandas versions.
    with pytest.raises(TypeError, match="resolution must be a string"):
        MeasurementMetadata("p", "kW", resolution=pd.Timedelta("15min"))


@pytest.mark.parametrize("field", ["name", "timezone"])
def test_non_string_name_or_timezone(field):
    with pytest.raises(TypeError, match=f"{field} must be a string"):
        MeasurementMetadata(**{"name": "p", "unit": "kW", field: 5})
