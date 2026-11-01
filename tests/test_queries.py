"""Validate Core query construction without executing SQL."""

import pytest
from sqlalchemy.dialects import sqlite

from mcp_data_gw.errors import GatewayError
from mcp_data_gw.models import Metric, Sort
from mcp_data_gw.queries import (
    build_aggregate_statement,
    build_select_statement,
    metric_name,
    validate_aggregation,
    validate_select,
)

pytestmark = pytest.mark.unit


def test_select_projection_filter_order_and_limit(tables):
    table = tables["Observation"]
    statement = build_select_statement(
        table,
        ["survived", "pclass"],
        table.c.age >= 18,
        [Sort(column="age", direction="desc"), Sort(column="pclass")],
        5,
    )
    assert list(statement.selected_columns.keys()) == ["survived", "pclass"]
    compiled = statement.compile(dialect=sqlite.dialect())
    sql = str(compiled)
    assert 'WHERE "Observation".age >= ?' in sql
    assert 'ORDER BY "Observation".age DESC, "Observation".pclass ASC' in sql
    assert "LIMIT ?" in sql
    assert 5 in compiled.params.values() and 18 in compiled.params.values()


def test_select_without_optional_clauses(tables):
    statement = build_select_statement(tables["Sex"], ["sex"], None, [], 200)
    assert list(statement.selected_columns.keys()) == ["sex"]
    assert "WHERE" not in str(statement) and "ORDER BY" not in str(statement)
    assert 200 in statement.compile().params.values()


@pytest.mark.parametrize(
    ("function", "column"),
    [
        ("count", None),
        ("count", "age"),
        ("sum", "fare"),
        ("avg", "survived"),
        ("min", "age"),
        ("max", "age"),
    ],
)
def test_aggregate_functions_and_explicit_source(tables, function, column):
    metric = Metric(function=function, column=column)
    statement = build_aggregate_statement(tables["Observation"], [metric], [], None, [], 50)
    assert list(statement.selected_columns.keys()) == [metric_name(metric)]
    sql = str(statement.compile(dialect=sqlite.dialect()))
    assert f"{function}(" in sql.lower()
    assert 'FROM "Observation"' in sql
    if column is None:
        assert "count(*)" in sql.lower()
    else:
        assert f'"Observation".{column}' in sql


def test_aggregate_group_filter_alias_order_and_limit(tables):
    table = tables["Observation"]
    statement = build_aggregate_statement(
        table,
        [Metric(function="avg", column="survived", alias="rate")],
        ["pclass"],
        table.c.age >= 18,
        [Sort(column="rate", direction="desc"), Sort(column="pclass")],
        3,
    )
    assert list(statement.selected_columns.keys()) == ["pclass", "rate"]
    sql = str(statement.compile(dialect=sqlite.dialect()))
    assert 'GROUP BY "Observation".pclass' in sql
    assert "WHERE" in sql and "ORDER BY" in sql and "DESC" in sql and "LIMIT" in sql
    assert 3 in statement.compile().params.values()


def test_count_all_keeps_filter_order_and_limit(tables):
    table = tables["Observation"]
    statement = build_aggregate_statement(
        table,
        [Metric(function="count", alias="total")],
        [],
        table.c.age >= 18,
        [Sort(column="total", direction="desc")],
        1,
    )
    compiled = statement.compile(dialect=sqlite.dialect())
    sql = str(compiled)
    assert 'FROM "Observation"' in sql
    assert 'WHERE "Observation".age >= ?' in sql
    assert "ORDER BY total DESC" in sql
    assert "LIMIT ?" in sql
    assert 18 in compiled.params.values() and 1 in compiled.params.values()


@pytest.mark.parametrize("alias", ["rate", "age", "select", "MixedCase"])
def test_metric_order_uses_selected_expression_not_a_sql_function(tables, alias):
    statement = build_aggregate_statement(
        tables["Observation"],
        [Metric(function="avg", column="survived", alias=alias)],
        ["pclass"],
        None,
        [Sort(column=alias, direction="desc")],
        50,
    )
    compiled = statement.compile(dialect=sqlite.dialect())
    sql = str(compiled)
    assert "column(" not in sql.lower()
    assert alias not in compiled.params.values()
    assert str(
        statement.selected_columns[alias].desc().compile(dialect=sqlite.dialect())
    ) in sql or (f'ORDER BY "{alias}" DESC' in sql or f"ORDER BY {alias} DESC" in sql)


@pytest.mark.parametrize(
    "columns", [[], ["age", "age"], ["rowid"], ["age; DROP TABLE Observation"]]
)
def test_select_validation(tables, columns):
    with pytest.raises(GatewayError):
        validate_select(tables["Observation"], columns, [])


@pytest.mark.parametrize(
    ("metrics", "groups", "sorts"),
    [
        ([], [], []),
        ([Metric(function="avg")], [], []),
        ([Metric(function="avg", column="alone")], [], []),
        ([Metric(function="count"), Metric(function="count")], [], []),
        ([Metric(function="count", alias="age")], ["age"], []),
        ([Metric(function="count")], ["age", "age"], []),
        ([Metric(function="count")], [], [Sort(column="age")]),
    ],
)
def test_aggregation_validation(tables, metrics, groups, sorts):
    with pytest.raises(GatewayError):
        validate_aggregation(tables["Observation"], metrics, groups, sorts)


def test_text_sum_rejected_and_min_allowed(tables):
    with pytest.raises(GatewayError, match="INVALID_AGGREGATION"):
        validate_aggregation(tables["Sex"], [Metric(function="sum", column="sex")], [], [])
    validate_aggregation(tables["Sex"], [Metric(function="min", column="sex")], [], [])


@pytest.mark.parametrize("alias", ["", "1name", "a-b", "x" * 65, "sql()"])
def test_invalid_alias_models(alias):
    with pytest.raises(ValueError):
        Metric(function="count", alias=alias)
