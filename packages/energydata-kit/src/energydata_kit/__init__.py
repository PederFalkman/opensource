"""energydata-kit: framework-independent quality checks for energy time series."""

from __future__ import annotations

__version__ = "0.1.0.dev0"

from energydata_kit.flags import (
    FLAG_COLUMN,
    VALUE_COLUMN,
    QualityFlag,
    decode_flags,
    flag_series,
    missing_value_mask,
    non_finite_mask,
    non_numeric_mask,
    out_of_bounds_mask,
)
from energydata_kit.intervals import (
    Gap,
    duplicate_mask,
    expected_grid,
    find_duplicate_timestamps,
    find_missing_intervals,
    off_grid_mask,
)
from energydata_kit.metadata import (
    Aggregation,
    IntervalLabel,
    MeasurementMetadata,
    UnitError,
    units_compatible,
    validate_unit,
)
from energydata_kit.report import QualityReport, assess_quality, fingerprint_series
from energydata_kit.semantics import (
    MetadataIssue,
    check_metadata_consistency,
    interval_bounds,
    local_day_completeness,
    relabel_intervals,
)
from energydata_kit.synthetic import make_synthetic_series
from energydata_kit.timestamps import (
    TimestampError,
    TimestampSummary,
    infer_resolution,
    normalize_timestamps,
    summarize_timestamps,
)

__all__ = [
    "FLAG_COLUMN",
    "VALUE_COLUMN",
    "Aggregation",
    "Gap",
    "IntervalLabel",
    "MeasurementMetadata",
    "MetadataIssue",
    "QualityFlag",
    "QualityReport",
    "TimestampError",
    "TimestampSummary",
    "UnitError",
    "__version__",
    "assess_quality",
    "check_metadata_consistency",
    "decode_flags",
    "duplicate_mask",
    "expected_grid",
    "find_duplicate_timestamps",
    "find_missing_intervals",
    "fingerprint_series",
    "flag_series",
    "infer_resolution",
    "interval_bounds",
    "local_day_completeness",
    "make_synthetic_series",
    "missing_value_mask",
    "non_finite_mask",
    "non_numeric_mask",
    "normalize_timestamps",
    "off_grid_mask",
    "out_of_bounds_mask",
    "relabel_intervals",
    "summarize_timestamps",
    "units_compatible",
    "validate_unit",
]
