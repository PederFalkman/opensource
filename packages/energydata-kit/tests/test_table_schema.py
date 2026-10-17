import json

import pytest

from energydata_kit import MeasurementMetadata, from_table_schema, to_table_schema
from energydata_kit.table_schema import NAMESPACE

META = MeasurementMetadata(
    name="import_energy",
    unit="kWh",
    quantity="energy",
    resolution="15min",
    aggregation="sum",
    interval_label="end",
    timezone="Europe/Stockholm",
    description="Synthetic example",
)

# Field types defined by Table Schema v1.
TABLE_SCHEMA_TYPES = {
    "string", "number", "integer", "boolean", "object", "array", "date", "time",
    "datetime", "year", "yearmonth", "duration", "geopoint", "geojson", "any",
}  # fmt: skip


def test_structure_follows_table_schema():
    schema = to_table_schema(META, include_flag=True)
    assert schema["primaryKey"] == ["timestamp"]
    names = [f["name"] for f in schema["fields"]]
    assert names == ["timestamp", "import_energy", "quality_flag"]
    assert all(f["type"] in TABLE_SCHEMA_TYPES for f in schema["fields"])
    ts, value, flag = schema["fields"]
    assert ts["type"] == "datetime" and ts["constraints"] == {"required": True}
    assert "end" in ts["description"]
    assert value["description"] == "Synthetic example"
    assert value[NAMESPACE]["unit"] == "kWh" and value[NAMESPACE]["aggregation"] == "sum"
    assert flag["constraints"] == {"required": True, "minimum": 0, "maximum": 65535}
    json.dumps(schema)  # plain JSON


def test_round_trip_through_json():
    schema = json.loads(json.dumps(to_table_schema(META)))
    assert from_table_schema(schema) == META


def test_without_description_or_flag():
    schema = to_table_schema(MeasurementMetadata(name="p", unit="kW"), timestamp_field="time")
    assert [f["name"] for f in schema["fields"]] == ["time", "p"]
    assert "description" not in schema["fields"][1]
    assert from_table_schema(schema).description == ""


def test_field_selection_and_errors():
    a = to_table_schema(META)
    b = to_table_schema(MeasurementMetadata(name="export_energy", unit="kWh"))
    merged = {"fields": [*a["fields"], b["fields"][1]], "primaryKey": ["timestamp"]}
    with pytest.raises(ValueError, match="found 2"):
        from_table_schema(merged)
    assert from_table_schema(merged, field="export_energy").name == "export_energy"
    with pytest.raises(ValueError, match="found 0"):
        from_table_schema({"fields": [{"name": "x", "type": "number"}]})
    with pytest.raises(ValueError, match="must differ"):
        to_table_schema(MeasurementMetadata(name="timestamp", unit="kW"))


def test_invalid_metadata_in_schema_is_rejected():
    schema = to_table_schema(META)
    schema["fields"][1][NAMESPACE]["unit"] = "kilowombat"
    with pytest.raises(ValueError):
        from_table_schema(schema)


def test_flag_column_name_clash_rejected():
    meta = MeasurementMetadata("quality_flag", "kW")
    assert len(to_table_schema(meta)["fields"]) == 2  # fine without the flag column
    with pytest.raises(ValueError, match="no other field may be named 'quality_flag'"):
        to_table_schema(meta, include_flag=True)


def test_name_inside_the_namespace_is_rejected():
    # It would silently relabel the column: the report for "import_energy"
    # carried metadata named "other".
    schema = to_table_schema(META)
    schema["fields"][1][NAMESPACE]["name"] = "other"
    with pytest.raises(ValueError, match="belong on the field"):
        from_table_schema(schema)


@pytest.mark.parametrize(
    ("schema", "message"),
    [
        ([], "expected an object with a 'fields' list"),
        ({"fields": None}, "expected an object with a 'fields' list"),
        ({"fields": [NAMESPACE]}, "found 0"),
        ({"fields": [{NAMESPACE: {"unit": "kW"}}]}, "no string 'name'"),
        ({"fields": [{"name": "p", NAMESPACE: ["kW"]}]}, "must be an object"),
        ({"fields": [{"name": "p", NAMESPACE: {}}]}, "field 'p': invalid"),
        ({"fields": [{"name": "p", NAMESPACE: {"unit": "kW", "colour": "red"}}]}, "field 'p': invalid"),
    ],
)
def test_malformed_schema_raises_value_error(schema, message):
    with pytest.raises(ValueError, match=message):
        from_table_schema(schema)
