"""Compare two quality reports, e.g. before and after a data fix.

Works on reports as produced by :func:`energydata_kit.assess_quality` and
:func:`energydata_kit.assess_frame`, either as report objects or as the
dictionaries their JSON loads into, so saved reports can be compared later.
The comparison states what changed; it does not judge whether the data got
better, apart from the narrowly defined :attr:`ReportComparison.worse`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from energydata_kit import __version__
from energydata_kit.frame_report import FrameQualityReport
from energydata_kit.report import REPORT_SCHEMA_VERSION, QualityReport

# Report schemas this package can read; comparisons are always written as the current one.
_READABLE_SCHEMAS = ("1", REPORT_SCHEMA_VERSION)

__all__ = ["ReportComparison", "compare_reports"]

_COUNTS = (
    "n_rows",
    "n_expected_intervals",
    "n_missing_intervals",
    "n_missing_explained",
    "n_gaps",
    "n_duplicate_timestamps",
)

ReportLike = QualityReport | FrameQualityReport | dict[str, Any]


@dataclass(frozen=True)
class ReportComparison:
    """What changed between two reports.

    ``changes`` holds one entry per series (key ``""`` for single-series
    reports, the column name for frame reports).
    """

    same_data: bool
    worse: bool
    changes: dict[str, dict[str, Any]]
    columns_added: list[str] = field(default_factory=list)
    columns_removed: list[str] = field(default_factory=list)
    package_version: str = __version__
    schema_version: str = REPORT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """The comparison as plain JSON-compatible data (what ``to_json`` writes)."""
        return {
            "schema_version": self.schema_version,
            "package_version": self.package_version,
            "same_data": self.same_data,
            "worse": self.worse,
            "columns_added": self.columns_added,
            "columns_removed": self.columns_removed,
            "changes": self.changes,
        }

    def to_json(self, indent: int | None = 2) -> str:
        """Deterministic JSON (sorted keys, fixed separators)."""
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True, ensure_ascii=True)


def _as_dict(report: ReportLike) -> dict[str, Any]:
    if isinstance(report, QualityReport | FrameQualityReport):
        return report.to_dict()
    if not isinstance(report, dict):
        raise TypeError(f"expected a report or a report dict, got {type(report).__name__}")
    return report


def _require(ok: bool, side: str, where: str, expected: str) -> None:
    if not ok:
        raise ValueError(f"{side} is not a quality report: {where} must be {expected}")


def _is_count(value: Any) -> bool:
    return value is None or (isinstance(value, int) and not isinstance(value, bool))


def _check_series(data: Any, side: str, where: str) -> None:
    """Reject a dict lacking the single-series report fields the comparison reads."""
    _require(isinstance(data, dict), side, where or "the report", "an object")
    prefix = f"{where}." if where else ""
    _require(isinstance(data.get("fingerprint"), str), side, f"{prefix}fingerprint", "a string")
    flags = data.get("flag_counts")
    _require(
        isinstance(flags, dict) and all(_is_count(v) and v is not None for v in flags.values()),
        side,
        f"{prefix}flag_counts",
        "an object of counts",
    )
    for key in _COUNTS:
        _require(_is_count(data.get(key)), side, f"{prefix}{key}", "a count or null")
    for key in ("completeness", "completeness_excluding_outages"):
        share = data.get(key)
        _require(
            share is None or (isinstance(share, int | float) and not isinstance(share, bool)),
            side,
            f"{prefix}{key}",
            "a number or null",
        )
    gaps = data.get("gaps")
    _require(
        isinstance(gaps, list)
        and all(
            isinstance(g, dict)
            and isinstance(g.get("start"), str)
            and isinstance(g.get("end"), str)
            and g.get("missing_count") is not None
            and _is_count(g["missing_count"])
            for g in gaps
        ),
        side,
        f"{prefix}gaps",
        "a list of gaps with start, end and missing_count",
    )
    issues = data.get("metadata_issues")
    _require(
        isinstance(issues, list)
        and all(isinstance(i, dict) and isinstance(i.get("code"), str) for i in issues),
        side,
        f"{prefix}metadata_issues",
        "a list of issues with a code",
    )
    for key in ("parameters", "metadata", "truncated"):
        _require(
            data.get(key) is None or isinstance(data[key], dict), side, f"{prefix}{key}", "an object or null"
        )


def _check_report(data: dict[str, Any], side: str) -> None:
    """Reject input that is not a report (e.g. a saved comparison), naming the first bad field."""
    if "columns" not in data:
        _check_series(data, side, "")
        return
    columns = data["columns"]
    _require(isinstance(columns, dict), side, "columns", "an object")
    _require(isinstance(data.get("fingerprint"), str), side, "fingerprint", "a string")
    order = data.get("column_order", list(columns))
    _require(
        isinstance(order, list) and sorted(map(str, order)) == sorted(columns),
        side,
        "column_order",
        "the list of column names",
    )
    for name, column in columns.items():
        _check_series(column, side, f"columns.{name}")


def _pair(before: Any, after: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {"before": before, "after": after}
    if isinstance(before, int | float) and isinstance(after, int | float):
        delta = after - before
        entry["delta"] = round(delta, 6) if isinstance(delta, float) else delta
    return entry


def _changed_keys(before: dict[str, Any] | None, after: dict[str, Any] | None) -> dict[str, Any]:
    before, after = before or {}, after or {}
    return {
        key: {"before": before.get(key), "after": after.get(key)}
        for key in sorted(set(before) | set(after))
        if before.get(key) != after.get(key)
    }


def _gap_key(gap: dict[str, Any]) -> tuple[str, str, int]:
    return (gap["start"], gap["end"], gap["missing_count"])


def _gap(key: tuple[str, str, int]) -> dict[str, Any]:
    return dict(zip(("start", "end", "missing_count"), key, strict=True))


def _match_gaps(before: set[tuple[str, str, int]], after: set[tuple[str, str, int]]) -> dict[str, list[Any]]:
    """Resolved, new and changed gaps (schema 2, P-10).

    Exact matches are left out. Two remaining gaps whose intervals (both ends
    included) overlap are a changed pair; a gap overlapping several on the
    other side (one split in two, or two merged) is paired with each. Gaps
    overlapping nothing on the other side are resolved or new.
    """

    def bounds(keys: set[tuple[str, str, int]]) -> list[tuple[int, int, tuple[str, str, int]]]:
        return sorted((pd.Timestamp(k[0]).value, pd.Timestamp(k[1]).value, k) for k in keys)

    b_list, a_list = bounds(before - after), bounds(after - before)
    changed: list[dict[str, Any]] = []
    paired_b: set[tuple[str, str, int]] = set()
    paired_a: set[tuple[str, str, int]] = set()
    # Gaps on one side never overlap each other, so sorted by start they are
    # also sorted by end: a sweep finds every overlapping pair.
    j = 0
    for b_start, b_end, b_key in b_list:
        while j < len(a_list) and a_list[j][1] < b_start:
            j += 1
        k = j
        while k < len(a_list) and a_list[k][0] <= b_end:
            a_key = a_list[k][2]
            changed.append({"before": _gap(b_key), "after": _gap(a_key)})
            paired_b.add(b_key)
            paired_a.add(a_key)
            k += 1
    return {
        "resolved": [_gap(k) for _, _, k in b_list if k not in paired_b],
        "new": [_gap(k) for _, _, k in a_list if k not in paired_a],
        "changed": changed,
    }


def _compare_series(before: dict[str, Any], after: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Changes between two single-series report dicts, and whether ``after`` is worse."""
    changes: dict[str, Any] = {}
    for key in ("fingerprint", "first_timestamp", "last_timestamp"):
        if before.get(key) != after.get(key):
            changes[key] = _pair(before.get(key), after.get(key))
    counts = {k: _pair(before.get(k), after.get(k)) for k in _COUNTS if before.get(k) != after.get(k)}
    for key in ("completeness", "completeness_excluding_outages"):
        if before.get(key) != after.get(key):
            counts[key] = _pair(before.get(key), after.get(key))
    if counts:
        changes["counts"] = counts

    b_flags, a_flags = before.get("flag_counts", {}), after.get("flag_counts", {})
    # A flag one side does not report (a schema-1 report has no COUNTER_ROLLOVER) is not
    # compared: a missing count is unknown, not zero.
    flags = {
        name: _pair(b_flags[name], a_flags[name])
        for name in sorted(set(b_flags) & set(a_flags))
        if b_flags[name] != a_flags[name]
    }
    if flags:
        changes["flag_counts"] = flags

    b_gaps = {_gap_key(g) for g in before.get("gaps", [])}
    a_gaps = {_gap_key(g) for g in after.get("gaps", [])}
    if b_gaps != a_gaps:
        changes["gaps"] = {
            **_match_gaps(b_gaps, a_gaps),
            # Only listed gaps are compared; truncated lists may hide some.
            "lists_truncated": bool(
                (before.get("truncated") or {}).get("gaps") or (after.get("truncated") or {}).get("gaps")
            ),
        }

    b_issues = {i["code"] for i in before.get("metadata_issues", [])}
    a_issues = {i["code"] for i in after.get("metadata_issues", [])}
    if b_issues != a_issues:
        changes["metadata_issues"] = {
            "resolved": sorted(b_issues - a_issues),
            "new": sorted(a_issues - b_issues),
        }

    for key in ("parameters", "metadata"):
        diff = _changed_keys(before.get(key), after.get(key))
        if diff:
            changes[key] = diff

    # Missing intervals inside known outages are explained, not worse (P-24, as report's
    # --fail-on-issues since P-21); with outages on both sides, so is completeness.
    def unexplained(r: dict[str, Any]) -> int:
        return (r.get("n_missing_intervals") or 0) - (r.get("n_missing_explained") or 0)

    key = "completeness"
    if (
        before.get("completeness_excluding_outages") is not None
        and after.get("completeness_excluding_outages") is not None
    ):
        key = "completeness_excluding_outages"
    worse = (
        a_flags.get("ANY", 0) > b_flags.get("ANY", 0)
        or unexplained(after) > unexplained(before)
        or (before.get(key) is not None and after.get(key) is not None and after[key] < before[key])
    )
    return changes, worse


def compare_reports(before: ReportLike, after: ReportLike) -> ReportComparison:
    """Compare two reports of the same kind.

    Reports of schema 1 (energydata-kit 0.1.0) and 2 can be compared, also
    with each other; the comparison is written as schema 2. A flag count
    only one side reports (``COUNTER_ROLLOVER`` is new in schema 2) is not
    compared, and parameters a schema-1 report lacks read as ``None``.

    Single-series reports are compared directly. Frame reports are compared
    column by column; added and removed columns are listed.

    For each series, the result lists only what differs: fingerprint and time
    range, counts (rows, expected and missing intervals, gaps, duplicates,
    completeness) with deltas, flag counts, listed gaps that were resolved,
    are new or changed, metadata issue codes, and changed parameters or
    metadata. Gaps are matched by overlap: identical gaps are unchanged and
    not listed; a gap whose interval overlaps one on the other side with
    different bounds (it shrank, grew or moved) is listed under ``changed``
    as a ``{"before": ..., "after": ...}`` pair, once per overlapping pair
    when a gap was split or merged; ``resolved`` and ``new`` hold only gaps
    that overlap nothing on the other side. Only listed gaps are compared;
    see ``lists_truncated``.

    ``worse`` is true if, for any series present in both reports, rows were
    flagged more often (``flag_counts["ANY"]``), more intervals are missing
    outside known outages (``n_missing_intervals - n_missing_explained``),
    or completeness fell; when both reports record known outages,
    ``completeness_excluding_outages`` is compared instead of
    ``completeness``. A removed column does not count as worse; check
    ``columns_removed``.

    Raises ``ValueError`` for another ``schema_version``, for a
    single-series report against a frame report, and for input that lacks
    the report fields the comparison reads (e.g. a saved comparison, or a
    hand-edited report); the message names the first bad field.
    """
    b, a = _as_dict(before), _as_dict(after)
    for side, data in (("before", b), ("after", a)):
        if data.get("schema_version") not in _READABLE_SCHEMAS:
            raise ValueError(
                f"{side} report has schema_version {data.get('schema_version')!r}; "
                f"this package compares schemas {', '.join(_READABLE_SCHEMAS)}"
            )
        _check_report(data, side)
    b_frame, a_frame = "columns" in b, "columns" in a
    if b_frame != a_frame:
        raise ValueError("cannot compare a single-series report with a multi-column report")

    if not b_frame:
        changes, worse = _compare_series(b, a)
        return ReportComparison(
            same_data=b.get("fingerprint") == a.get("fingerprint"),
            worse=worse,
            changes={"": changes},
        )

    b_cols, a_cols = b["columns"], a["columns"]
    order = [c for c in b.get("column_order", list(b_cols)) if c in a_cols]
    per_column: dict[str, dict[str, Any]] = {}
    any_worse = False
    for name in order:
        per_column[name], worse = _compare_series(b_cols[name], a_cols[name])
        any_worse |= worse
    return ReportComparison(
        same_data=b.get("fingerprint") == a.get("fingerprint"),
        worse=any_worse,
        changes=per_column,
        columns_added=[c for c in a.get("column_order", list(a_cols)) if c not in b_cols],
        columns_removed=[c for c in b.get("column_order", list(b_cols)) if c not in a_cols],
    )
