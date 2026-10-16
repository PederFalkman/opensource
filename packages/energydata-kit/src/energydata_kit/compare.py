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

from energydata_kit import __version__
from energydata_kit.frame_report import FrameQualityReport
from energydata_kit.report import REPORT_SCHEMA_VERSION, QualityReport

__all__ = ["ReportComparison", "compare_reports"]

_COUNTS = (
    "n_rows",
    "n_expected_intervals",
    "n_missing_intervals",
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


def _compare_series(before: dict[str, Any], after: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Changes between two single-series report dicts, and whether ``after`` is worse."""
    changes: dict[str, Any] = {}
    for key in ("fingerprint", "first_timestamp", "last_timestamp"):
        if before.get(key) != after.get(key):
            changes[key] = _pair(before.get(key), after.get(key))
    counts = {k: _pair(before.get(k), after.get(k)) for k in _COUNTS if before.get(k) != after.get(k)}
    if before.get("completeness") != after.get("completeness"):
        counts["completeness"] = _pair(before.get("completeness"), after.get("completeness"))
    if counts:
        changes["counts"] = counts

    b_flags, a_flags = before.get("flag_counts", {}), after.get("flag_counts", {})
    flags = {
        name: _pair(b_flags.get(name, 0), a_flags.get(name, 0))
        for name in sorted(set(b_flags) | set(a_flags))
        if b_flags.get(name, 0) != a_flags.get(name, 0)
    }
    if flags:
        changes["flag_counts"] = flags

    b_gaps = {_gap_key(g) for g in before.get("gaps", [])}
    a_gaps = {_gap_key(g) for g in after.get("gaps", [])}
    if b_gaps != a_gaps:
        changes["gaps"] = {
            "resolved": [
                dict(zip(("start", "end", "missing_count"), g, strict=True)) for g in sorted(b_gaps - a_gaps)
            ],
            "new": [
                dict(zip(("start", "end", "missing_count"), g, strict=True)) for g in sorted(a_gaps - b_gaps)
            ],
            # Only listed gaps are compared; truncated lists may hide some.
            "lists_truncated": bool(
                before.get("truncated", {}).get("gaps") or after.get("truncated", {}).get("gaps")
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

    worse = (
        a_flags.get("ANY", 0) > b_flags.get("ANY", 0)
        or (after.get("n_missing_intervals") or 0) > (before.get("n_missing_intervals") or 0)
        or (
            before.get("completeness") is not None
            and after.get("completeness") is not None
            and after["completeness"] < before["completeness"]
        )
    )
    return changes, worse


def compare_reports(before: ReportLike, after: ReportLike) -> ReportComparison:
    """Compare two reports of the same kind and report schema.

    Single-series reports are compared directly. Frame reports are compared
    column by column; added and removed columns are listed.

    For each series, the result lists only what differs: fingerprint and time
    range, counts (rows, expected and missing intervals, gaps, duplicates,
    completeness) with deltas, flag counts, listed gaps that were resolved or
    are new, metadata issue codes, and changed parameters or metadata.
    Gaps are matched exactly, so a gap that shrank appears once as resolved
    and once (smaller) as new. Only listed gaps are compared; see
    ``lists_truncated``.

    ``worse`` is true if, for any series present in both reports, rows were
    flagged more often (``flag_counts["ANY"]``), more intervals are missing,
    or completeness fell. A removed column does not count as worse; check
    ``columns_removed``.
    """
    b, a = _as_dict(before), _as_dict(after)
    for side, data in (("before", b), ("after", a)):
        if data.get("schema_version") != REPORT_SCHEMA_VERSION:
            raise ValueError(
                f"{side} report has schema_version {data.get('schema_version')!r}; "
                f"this package compares schema {REPORT_SCHEMA_VERSION}"
            )
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
