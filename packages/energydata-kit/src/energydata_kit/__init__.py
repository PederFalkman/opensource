"""energydata-kit: framework-independent quality checks for energy time series."""

from __future__ import annotations

__version__ = "0.3.0.dev0"

from energydata_kit.compare import ReportComparison, compare_reports
from energydata_kit.flags import (
    FLAG_COLUMN,
    VALUE_COLUMN,
    QualityFlag,
    counter_decrease_mask,
    counter_rollover_mask,
    decode_flags,
    flag_series,
    jump_mask,
    jump_rate_mask,
    missing_value_mask,
    non_finite_mask,
    non_numeric_mask,
    out_of_bounds_mask,
    stale_mask,
)
from energydata_kit.frame_report import FrameQualityReport, assess_frame, flag_column, flag_frame
from energydata_kit.intervals import (
    Gap,
    duplicate_mask,
    expected_grid,
    find_duplicate_timestamps,
    find_missing_intervals,
    missing_timestamps,
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
from energydata_kit.table_schema import from_table_schema, to_table_schema
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
    "FrameQualityReport",
    "Gap",
    "IntervalLabel",
    "MeasurementMetadata",
    "MetadataIssue",
    "QualityFlag",
    "QualityReport",
    "ReportComparison",
    "TimestampError",
    "TimestampSummary",
    "UnitError",
    "__version__",
    "assess_frame",
    "assess_quality",
    "check_metadata_consistency",
    "compare_reports",
    "counter_decrease_mask",
    "counter_rollover_mask",
    "decode_flags",
    "duplicate_mask",
    "expected_grid",
    "find_duplicate_timestamps",
    "find_missing_intervals",
    "fingerprint_series",
    "flag_column",
    "flag_frame",
    "flag_series",
    "from_table_schema",
    "infer_resolution",
    "interval_bounds",
    "jump_mask",
    "jump_rate_mask",
    "local_day_completeness",
    "make_synthetic_series",
    "missing_timestamps",
    "missing_value_mask",
    "non_finite_mask",
    "non_numeric_mask",
    "normalize_timestamps",
    "off_grid_mask",
    "out_of_bounds_mask",
    "relabel_intervals",
    "stale_mask",
    "summarize_timestamps",
    "to_table_schema",
    "units_compatible",
    "validate_unit",
]
