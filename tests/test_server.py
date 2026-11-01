"""Official in-process MCP tests with only the database boundary mocked."""

import asyncio

import pytest
from mcp import Client
from sqlalchemy.exc import OperationalError

from mcp_data_gw.models import Metric
from mcp_data_gw.server import create_server

pytestmark = pytest.mark.integration


def test_exact_tool_catalog_and_structured_metadata(service):
    async def scenario():
        async with Client(create_server(service), raise_exceptions=True) as client:
            tools = await client.list_tools()
            assert {tool.name for tool in tools.tools} == {
                "list_tables",
                "describe_table",
                "select_rows",
                "aggregate_rows",
            }
            for tool in tools.tools:
                assert tool.title
                assert tool.annotations.read_only_hint is True
                assert tool.annotations.destructive_hint is False
                assert tool.annotations.open_world_hint is False
                assert tool.annotations.idempotent_hint is True
                assert "Returns:" in tool.description
                if tool.name != "list_tables":
                    assert "Args:" in tool.description
            result = await client.call_tool("list_tables")
            assert not result.is_error
            assert len(result.structured_content["tables"]) == 8
            result = await client.call_tool("describe_table", {"table": "Observation"})
            assert not result.is_error
            assert result.structured_content["columns"][0]["primary_key"] is False

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("name", "arguments"),
    [
        ("describe_table", {"table": "sqlite_master"}),
        ("select_rows", {"table": "Observation", "columns": ["rowid"]}),
        ("select_rows", {"table": "Observation", "columns": ["age"], "limit": 0}),
        (
            "select_rows",
            {
                "table": "Observation",
                "columns": ["age"],
                "where": {
                    "column": "age",
                    "operator": "eq",
                    "value": "18",
                },
            },
        ),
        ("aggregate_rows", {"table": "Observation", "metrics": [{"function": "avg"}]}),
    ],
)
def test_invalid_inputs_are_tool_errors(service, name, arguments):
    async def scenario():
        async with Client(create_server(service), raise_exceptions=True) as client:
            result = await client.call_tool(name, arguments)
            assert result.is_error

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "error",
    [
        RuntimeError("secret /private/path password=hidden"),
        OperationalError("SELECT secret", {}, RuntimeError("password=hidden")),
    ],
)
def test_sanitized_failures(service, database, error, caplog):
    database.list_tables.side_effect = error

    async def scenario():
        async with Client(create_server(service), raise_exceptions=True) as client:
            result = await client.call_tool("list_tables")
            assert result.is_error
            message = str(result.content)
            assert "reference" in message
            assert (
                "secret" not in message and "password" not in message and "/private" not in message
            )

    asyncio.run(scenario())
    assert "tool_failure" in caplog.text
    assert "password=hidden" not in caplog.text


def test_select_native_json_owner_acceptance(service, database):
    database.execute.return_value = [{"age": None, "alone": True, "survived": 1}]

    async def scenario():
        async with Client(create_server(service), raise_exceptions=True) as client:
            result = await client.call_tool(
                "select_rows",
                {
                    "table": "Observation",
                    "columns": ["age", "alone", "survived"],
                },
            )
            assert not result.is_error
            assert result.structured_content == {
                "rows": [{"age": None, "alone": True, "survived": 1}],
                "returned_count": 1,
            }

    asyncio.run(scenario())


def test_aggregate_owner_acceptance(service, database):
    database.execute.return_value = [{"pclass": 1, "avg_survived": 0.6}]

    async def scenario():
        async with Client(create_server(service), raise_exceptions=True) as client:
            result = await client.call_tool(
                "aggregate_rows",
                {
                    "table": "Observation",
                    "metrics": [Metric(function="avg", column="survived").model_dump()],
                    "group_by": ["pclass"],
                },
            )
            assert not result.is_error
            assert result.structured_content["rows"][0]["avg_survived"] == 0.6

    asyncio.run(scenario())


def test_recursive_filter_schemas(service):
    async def scenario():
        async with Client(create_server(service), raise_exceptions=True) as client:
            catalog = await client.list_tools()
            for tool in catalog.tools:
                if tool.name not in {"select_rows", "aggregate_rows"}:
                    continue
                schema = tool.input_schema
                definitions = schema["$defs"]
                condition = definitions["Condition"]
                group = definitions["FilterGroup"]
                expected_refs = {"#/$defs/Condition", "#/$defs/FilterGroup"}
                assert {
                    item["$ref"]
                    for item in schema["properties"]["where"]["anyOf"]
                    if "$ref" in item
                } == expected_refs
                assert set(condition["required"]) == {"column", "operator"}
                assert "contains" in condition["properties"]["operator"]["enum"]
                assert group["properties"]["logic"]["enum"] == ["and", "or"]
                children = group["properties"]["conditions"]
                assert children["minItems"] == 1
                assert children["maxItems"] == 30
                assert {item["$ref"] for item in children["items"]["anyOf"]} == expected_refs
                assert condition["additionalProperties"] is False
                assert group["additionalProperties"] is False

    asyncio.run(scenario())


@pytest.mark.parametrize("name", ["select_rows", "aggregate_rows"])
def test_nested_filter_tool_calls(service, database, name):
    database.execute.return_value = []

    async def scenario():
        async with Client(create_server(service), raise_exceptions=True) as client:
            arguments = {
                "table": "Observation",
                "where": {
                    "logic": "or",
                    "conditions": [
                        {"column": "age", "operator": "is_null"},
                        {
                            "logic": "and",
                            "conditions": [{"column": "age", "operator": "gte", "value": 18}],
                        },
                    ],
                },
            }
            arguments.update(
                {"columns": ["age"]}
                if name == "select_rows"
                else {"metrics": [{"function": "count"}]}
            )
            result = await client.call_tool(name, arguments)
            assert not result.is_error
            statement = database.execute.call_args.args[0]
            assert "IS NULL" in str(statement)
            assert " OR " in str(statement)
            assert 18 in statement.compile().params.values()
            arguments["where"]["conditions"][0]["value"] = None
            database.execute.reset_mock()
            result = await client.call_tool(name, arguments)
            assert result.is_error
            database.execute.assert_not_called()

    asyncio.run(scenario())
