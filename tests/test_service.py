"""Semantic metadata, live lookup values, limits and repository interaction."""

import pytest

from mcp_data_gw.errors import GatewayError
from mcp_data_gw.metadata import SCHEMA

pytestmark = pytest.mark.unit


def test_catalog_is_sorted_and_restricted(service, database):
    assert [table.name for table in service.list_tables().tables] == sorted(SCHEMA)
    database.list_tables.return_value = []
    assert service.list_tables().tables == []


def test_description_has_real_metadata_and_separate_relationships(service, database):
    database.execute.side_effect = lambda statement: [
        {
            column.name: (42 if column.name.endswith("_id") else "current")
            for column in statement.selected_columns
        }
    ]
    result = service.describe_table("Observation")
    assert len(result.columns) == 15
    assert not any(column.primary_key for column in result.columns)
    assert result.declared_foreign_keys == []
    assert len(result.logical_relationships) == len(result.lookup_values) == 7
    assert all(column.description for column in result.columns)
    assert result.lookup_values[0].values[0].label == "current"
    database.execute.side_effect = lambda statement: [
        {
            column.name: (77 if column.name.endswith("_id") else "updated")
            for column in statement.selected_columns
        }
    ]
    updated = service.describe_table("Observation")
    assert updated.lookup_values[0].values[0].id == 77
    assert updated.lookup_values[0].values[0].label == "updated"


def test_large_lookup_fails_explicitly(service, database):
    database.execute.return_value = [{"alive_id": 1, "alive": "yes"}] * 201
    with pytest.raises(GatewayError, match="DATABASE_UNAVAILABLE"):
        service.describe_table("Observation")


@pytest.mark.parametrize("limit", [0, -1, 201, True, "50", 1.5])
def test_service_rejects_invalid_limits_before_database(service, database, limit):
    with pytest.raises(GatewayError, match="INVALID_ARGUMENT"):
        service.select_rows("Observation", ["age"], limit=limit)
    database.reflect.assert_not_called()


def test_select_empty_result_owner_acceptance(service):
    result = service.select_rows("Observation", ["age"])
    assert result.rows == [] and result.returned_count == 0
