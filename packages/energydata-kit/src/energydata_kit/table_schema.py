"""Export and import measurement metadata as a Frictionless Table Schema.

`Table Schema <https://specs.frictionlessdata.io/table-schema/>`_ is a plain
JSON format, so no dependency is needed. The spec allows extra properties on a
field; energydata-kit stores its metadata under one namespaced
``"energydata_kit"`` property so it round-trips without clashing with other
tools.
"""

from __future__ import annotations

from typing import Any

from energydata_kit.flags import FLAG_COLUMN
from energydata_kit.metadata import MeasurementMetadata

__all__ = ["NAMESPACE", "from_table_schema", "to_table_schema"]

NAMESPACE = "energydata_kit"
_UINT16_MAX = 65_535


def to_table_schema(
    metadata: MeasurementMetadata,
    *,
    timestamp_field: str = "timestamp",
    include_flag: bool = False,
) -> dict[str, Any]:
    """Describe a ``timestamp, value[, quality_flag]`` table as a Table Schema dict.

    The timestamp is the primary key. ``include_flag`` adds the
    ``quality_flag`` column produced by :func:`energydata_kit.flag_series`.
    """
    if timestamp_field == metadata.name:
        raise ValueError("timestamp_field and the measurement name must differ")
    extra = metadata.to_dict()
    name = extra.pop("name")
    description = extra.pop("description")

    value_field: dict[str, Any] = {"name": name, "type": "number", NAMESPACE: extra}
    if description:
        value_field["description"] = description

    fields: list[dict[str, Any]] = [
        {
            "name": timestamp_field,
            "type": "datetime",
            "description": f"Interval {metadata.interval_label.value} timestamp, ISO 8601 with UTC offset",
            "constraints": {"required": True},
        },
        value_field,
    ]
    if include_flag:
        fields.append(
            {
                "name": FLAG_COLUMN,
                "type": "integer",
                "description": "energydata-kit QualityFlag bitmask (0 = no issue)",
                "constraints": {"required": True, "minimum": 0, "maximum": _UINT16_MAX},
            }
        )
    return {"fields": fields, "primaryKey": [timestamp_field]}


def from_table_schema(schema: dict[str, Any], field: str | None = None) -> MeasurementMetadata:
    """Rebuild :class:`MeasurementMetadata` from a schema made by :func:`to_table_schema`.

    ``field`` picks the measurement column by name; by default the single
    field carrying the ``"energydata_kit"`` property is used.
    """
    candidates = [f for f in schema.get("fields", []) if NAMESPACE in f]
    if field is not None:
        candidates = [f for f in candidates if f.get("name") == field]
    if len(candidates) != 1:
        raise ValueError(
            f"expected exactly one field with {NAMESPACE!r} metadata"
            + (f" named {field!r}" if field else "")
            + f", found {len(candidates)}"
        )
    found = candidates[0]
    return MeasurementMetadata.from_dict(
        {"name": found["name"], "description": found.get("description", ""), **found[NAMESPACE]}
    )
