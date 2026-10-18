"""The public call signatures, pinned.

Rule (reviewed in OSS-13, before 0.1.0): required inputs are positional;
every optional argument is keyword-only. Each entry lists the parameters
in order; ``*`` marks the start of keyword-only parameters and ``=`` marks
an optional one. A change here is an API change: update the snapshot
deliberately and record it in the CHANGELOG.
"""

import importlib.util
import inspect

import pytest

import energydata_kit

CORE = {
    "MeasurementMetadata": (
        "name",
        "unit",
        "*",
        "quantity=",
        "resolution=",
        "aggregation=",
        "interval_label=",
        "timezone=",
        "description=",
    ),
    "assess_frame": (
        "frame",
        "*",
        "columns=",
        "metadata=",
        "freq=",
        "bounds=",
        "stale_min_run=",
        "stale_atol=",
        "stale_exclude=",
        "cumulative=",
        "counter_tolerance=",
        "jump_max_delta=",
        "origin=",
        "tz=",
        "per_column=",
        "known_outages=",
        "max_listed=",
    ),
    "assess_quality": (
        "series",
        "*",
        "metadata=",
        "freq=",
        "bounds=",
        "stale_min_run=",
        "stale_atol=",
        "stale_exclude=",
        "cumulative=",
        "counter_tolerance=",
        "jump_max_delta=",
        "origin=",
        "tz=",
        "known_outages=",
        "max_listed=",
    ),
    "check_metadata_consistency": ("metadata",),
    "compare_reports": ("before", "after"),
    "counter_decrease_mask": ("values", "*", "tolerance="),
    "decode_flags": ("value",),
    "duplicate_mask": ("index",),
    "expected_grid": ("index", "freq", "*", "start=", "end=", "origin=", "tz="),
    "find_duplicate_timestamps": ("index",),
    "find_missing_intervals": ("index", "freq", "*", "start=", "end=", "origin=", "tz="),
    "fingerprint_series": ("series",),
    "flag_column": ("name",),
    "flag_frame": (
        "frame",
        "*",
        "columns=",
        "freq=",
        "bounds=",
        "insert_missing=",
        "stale_min_run=",
        "stale_atol=",
        "stale_exclude=",
        "cumulative=",
        "counter_tolerance=",
        "jump_max_delta=",
        "origin=",
        "tz=",
        "per_column=",
    ),
    "flag_series": (
        "series",
        "*",
        "freq=",
        "bounds=",
        "insert_missing=",
        "stale_min_run=",
        "stale_atol=",
        "stale_exclude=",
        "cumulative=",
        "counter_tolerance=",
        "jump_max_delta=",
        "origin=",
        "tz=",
    ),
    "from_table_schema": ("schema", "*", "field="),
    "infer_resolution": ("index",),
    "interval_bounds": ("index", "freq", "label"),
    "jump_mask": ("values", "max_delta"),
    "local_day_completeness": ("index", "freq", "tz", "*", "interval_label=", "origin="),
    "make_synthetic_series": (
        "*",
        "start=",
        "periods=",
        "freq=",
        "seed=",
        "base=",
        "amplitude=",
        "noise=",
        "name=",
        "drop=",
        "duplicate=",
        "nan_at=",
        "inf_at=",
    ),
    "missing_timestamps": ("index", "freq", "*", "start=", "end=", "origin=", "tz="),
    "missing_value_mask": ("values",),
    "non_finite_mask": ("values",),
    "non_numeric_mask": ("values",),
    "normalize_timestamps": ("values", "*", "assume_tz=", "ambiguous=", "nonexistent="),
    "off_grid_mask": ("index", "freq", "*", "origin=", "tz="),
    "out_of_bounds_mask": ("values", "*", "lower=", "upper="),
    "relabel_intervals": ("index", "freq", "from_label", "to_label"),
    "stale_mask": ("values", "min_run", "*", "atol=", "exclude="),
    "summarize_timestamps": ("index",),
    "to_table_schema": ("metadata", "*", "timestamp_field=", "include_flag="),
    "units_compatible": ("unit_a", "unit_b"),
    "validate_unit": ("unit",),
}

PANDERA = {
    "counter_check": ("*", "tolerance="),
    "finite_check": (),
    "jump_check": ("max_delta",),
    "no_duplicate_timestamps_check": (),
    "no_missing_intervals_check": ("freq", "*", "origin=", "tz="),
    "on_grid_check": ("freq", "*", "origin=", "tz="),
    "series_schema": (
        "*",
        "metadata=",
        "freq=",
        "bounds=",
        "stale_min_run=",
        "stale_atol=",
        "stale_exclude=",
        "cumulative=",
        "counter_tolerance=",
        "jump_max_delta=",
        "origin=",
        "tz=",
        "nullable=",
    ),
    "stale_check": ("min_run", "*", "atol=", "exclude="),
    "timezone_aware_check": (),
    "within_bounds_check": ("*", "lower=", "upper="),
}


def shape(obj: object) -> tuple[str, ...]:
    parts, keyword_only = [], False
    for p in inspect.signature(obj).parameters.values():
        if p.kind is p.KEYWORD_ONLY and not keyword_only:
            parts.append("*")
            keyword_only = True
        parts.append(p.name + ("" if p.default is p.empty else "="))
    return tuple(parts)


def snapshot(module: object, names: list[str]) -> dict[str, tuple[str, ...]]:
    return {
        name: shape(getattr(module, name))
        for name in names
        if inspect.isfunction(getattr(module, name)) or name == "MeasurementMetadata"
    }


def test_all_exports_resolve():
    for name in energydata_kit.__all__:
        assert hasattr(energydata_kit, name), name


def test_core_signatures():
    assert snapshot(energydata_kit, energydata_kit.__all__) == CORE


@pytest.mark.skipif(importlib.util.find_spec("pandera") is None, reason="needs the pandera extra")
def test_pandera_signatures():
    from energydata_kit import pandera_checks

    assert snapshot(pandera_checks, pandera_checks.__all__) == PANDERA


def test_optional_arguments_are_keyword_only():
    for name, params in {**CORE, **PANDERA}.items():
        positional = params[: params.index("*")] if "*" in params else params
        assert not any(p.endswith("=") for p in positional), f"{name}: optional argument before '*'"
