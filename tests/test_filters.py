"""Validate pure filters and inspect compiled bound parameters without SQL execution."""

import pytest
from sqlalchemy.dialects import sqlite

from mcp_data_gw.errors import GatewayError
from mcp_data_gw.queries import build_filter_expression, parse_filter

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "operator", ["eq", "ne", "gt", "gte", "lt", "lte", "in", "is_null", "is_not_null"]
)
def test_operators(tables, operator):
    raw = {"column": "age", "operator": operator}
    if operator not in {"is_null", "is_not_null"}:
        raw["value"] = [18, 30] if operator == "in" else 18
    expression = build_filter_expression(tables["Observation"], parse_filter(raw))
    compiled = expression.compile(dialect=sqlite.dialect())
    assert "Observation" in str(compiled)
    if operator not in {"is_null", "is_not_null"}:
        assert compiled.params


def test_nested_logic(tables):
    expression = build_filter_expression(
        tables["Observation"],
        parse_filter(
            {
                "logic": "or",
                "conditions": [
                    {"column": "age", "operator": "lt", "value": 10},
                    {
                        "logic": "and",
                        "conditions": [
                            {"column": "fare", "operator": "gt", "value": 100},
                            {"column": "alone", "operator": "eq", "value": True},
                        ],
                    },
                ],
            }
        ),
    )
    sql = str(expression)
    assert " OR " in sql and " AND " in sql


def test_contains_is_literal_and_bound(tables):
    payload = "' OR 1=1 -- %_/"
    expression = build_filter_expression(
        tables["Sex"],
        parse_filter(
            {
                "column": "sex",
                "operator": "contains",
                "value": payload,
            }
        ),
    )
    compiled = expression.compile(dialect=sqlite.dialect())
    assert payload not in str(compiled)
    assert list(compiled.params.values()) == ["' OR 1=1 -- /%/_//"]
    assert "ESCAPE '/'" in str(compiled)


@pytest.mark.parametrize(
    "raw",
    [
        {"logic": "and", "conditions": []},
        {"column": "age", "operator": "in", "value": []},
        {"column": "age", "operator": "in", "value": list(range(101))},
        {"column": "age", "operator": "eq"},
        {"column": "age", "operator": "eq", "value": None},
        {"column": "age", "operator": "is_null", "value": None},
        {"column": "age", "operator": "sql", "value": 1},
        {"column": "age", "operator": "eq", "value": 1, "logic": "and", "conditions": []},
    ],
)
def test_invalid_structures(raw):
    with pytest.raises(GatewayError, match="INVALID_FILTER"):
        parse_filter(raw)


@pytest.mark.parametrize(
    ("column", "operator", "value"),
    [
        ("age", "eq", "18"),
        ("age", "eq", True),
        ("age", "contains", 18),
        ("age", "in", [18, None]),
        ("alone", "eq", 1),
        ("survived", "eq", 1.5),
        ("age", "eq", {"sql": "bad"}),
        ("age", "eq", float("inf")),
    ],
)
def test_incompatible_values(tables, column, operator, value):
    with pytest.raises(GatewayError, match="INVALID_FILTER"):
        build_filter_expression(
            tables["Observation"],
            parse_filter(
                {
                    "column": column,
                    "operator": operator,
                    "value": value,
                }
            ),
        )


def test_filter_complexity_limits():
    leaf = {"column": "age", "operator": "eq", "value": 18}
    node = leaf
    for _ in range(5):
        node = {"logic": "and", "conditions": [node]}
    assert parse_filter(node) is not None
    with pytest.raises(GatewayError, match="INVALID_FILTER"):
        parse_filter({"logic": "and", "conditions": [node]})
    with pytest.raises(GatewayError, match="INVALID_FILTER"):
        parse_filter(
            {
                "logic": "or",
                "conditions": [
                    {"logic": "and", "conditions": [leaf] * 16},
                    {"logic": "and", "conditions": [leaf] * 15},
                ],
            }
        )
