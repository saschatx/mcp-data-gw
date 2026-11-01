"""Metadata-only fixtures; no SQLite file or connection is created."""

from unittest.mock import Mock

import pytest
from sqlalchemy import BigInteger, Boolean, Column, Float, MetaData, Table, Text

from mcp_data_gw.database import Database
from mcp_data_gw.metadata import LOOKUPS, SCHEMA, validate_table
from mcp_data_gw.service import Service


@pytest.fixture
def tables() -> dict[str, Table]:
    metadata = MetaData()
    result = {}
    for name, columns in SCHEMA.items():
        result[name] = Table(
            name,
            metadata,
            *[
                Column(
                    column,
                    (
                        Boolean()
                        if column in {"adult_male", "alone"}
                        else Float()
                        if column in {"age", "fare"}
                        else Text()
                        if name in LOOKUPS and column == LOOKUPS[name][1]
                        else BigInteger()
                    ),
                )
                for column in columns
            ],
        )
    return result


@pytest.fixture
def database(tables: dict[str, Table]) -> Mock:
    database = Mock(spec=Database)

    def reflect(name: str) -> Table:
        validate_table(name)
        return tables[name]

    database.reflect.side_effect = reflect
    database.list_tables.return_value = [*SCHEMA, "sqlite_master", "Private"]
    database.foreign_keys.return_value = []
    database.execute.return_value = []
    return database


@pytest.fixture
def service(database: Mock) -> Service:
    return Service(database)


@pytest.fixture(autouse=True)
def isolate_response_logs(tmp_path, monkeypatch):
    """Keep tool response logs inside each test's temporary directory."""
    monkeypatch.setattr("mcp_data_gw.logging.MCP_RESPONSE_LOG", tmp_path / "responses.jsonl")
