"""Measurement metadata and unit validation.

Units are parsed with `Pint <https://pint.readthedocs.io>`_; energydata-kit
does not implement its own unit system. For unit-aware arrays and conversion,
use Pint or pint-pandas directly.
"""

from __future__ import annotations

import zoneinfo
from dataclasses import asdict, dataclass
from enum import StrEnum
from functools import lru_cache
from typing import Any

import pandas as pd
import pint

from energydata_kit.intervals import to_step

__all__ = [
    "Aggregation",
    "IntervalLabel",
    "MeasurementMetadata",
    "UnitError",
    "get_unit_registry",
    "units_compatible",
    "validate_unit",
]


class UnitError(ValueError):
    """Raised when a unit string cannot be parsed."""


class Aggregation(StrEnum):
    """How a value relates to its time interval."""

    INSTANTANEOUS = "instantaneous"  # sampled at the timestamp
    MEAN = "mean"  # average over the interval, e.g. mean power
    SUM = "sum"  # accumulated over the interval, e.g. energy
    MIN = "min"
    MAX = "max"


class IntervalLabel(StrEnum):
    """Which edge of an interval the timestamp refers to."""

    START = "start"  # 00:00 labels the interval 00:00-00:15
    END = "end"  # 00:15 labels the interval 00:00-00:15


@lru_cache(maxsize=1)
def get_unit_registry() -> pint.UnitRegistry[Any]:
    """Shared Pint registry, extended with reactive power (``var``)."""
    ureg: pint.UnitRegistry[Any] = pint.UnitRegistry()
    # Pint's default registry has no unit for reactive power. var is
    # dimensionally identical to VA; the distinction is semantic.
    ureg.define("volt_ampere_reactive = volt * ampere = var")
    return ureg


def validate_unit(unit: str) -> str:
    """Return ``unit`` unchanged if Pint can parse it, else raise :class:`UnitError`."""
    if not isinstance(unit, str) or not unit.strip():
        raise UnitError("unit must be a non-empty string")
    try:
        get_unit_registry().Unit(unit)
    except (pint.errors.UndefinedUnitError, pint.errors.DefinitionSyntaxError, ValueError) as exc:
        raise UnitError(f"unknown unit {unit!r}: {exc}") from exc
    return unit


def units_compatible(unit_a: str, unit_b: str) -> bool:
    """True if both units share a dimensionality (e.g. ``kW`` and ``MW``)."""
    ureg = get_unit_registry()
    a = ureg.Unit(validate_unit(unit_a))
    b = ureg.Unit(validate_unit(unit_b))
    return bool(a.dimensionality == b.dimensionality)


def _validate_resolution(resolution: str) -> None:
    """Accept a positive fixed step (``"15min"``) or calendar step (``"D"``, ``"MS"``)."""
    try:
        to_step(resolution)
        return
    except ValueError as fixed_error:
        try:
            offset = pd.tseries.frequencies.to_offset(resolution)
        except (ValueError, TypeError):
            raise fixed_error from None
        if isinstance(offset, pd.offsets.Tick) or offset.n <= 0:
            raise fixed_error from None


@dataclass(frozen=True)
class MeasurementMetadata:
    """Descriptive metadata for one measured time series.

    Metadata is validated on construction but never changes the data it
    describes.
    """

    name: str
    unit: str
    quantity: str | None = None
    resolution: str | None = None  # fixed ("15min") or calendar ("D", "MS", used with tz)
    aggregation: Aggregation = Aggregation.INSTANTANEOUS
    interval_label: IntervalLabel = IntervalLabel.START
    timezone: str = "UTC"
    description: str = ""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("name must be non-empty")
        validate_unit(self.unit)
        object.__setattr__(self, "aggregation", Aggregation(self.aggregation))
        object.__setattr__(self, "interval_label", IntervalLabel(self.interval_label))
        if self.resolution is not None:
            _validate_resolution(self.resolution)
        try:
            zoneinfo.ZoneInfo(self.timezone)
        except (zoneinfo.ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"unknown time zone {self.timezone!r}") from exc

    @property
    def resolution_timedelta(self) -> pd.Timedelta | None:
        """The resolution as a fixed ``Timedelta``; raises ``ValueError`` for calendar steps."""
        return None if self.resolution is None else to_step(self.resolution)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["aggregation"] = self.aggregation.value
        data["interval_label"] = self.interval_label.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MeasurementMetadata:
        return cls(**data)
