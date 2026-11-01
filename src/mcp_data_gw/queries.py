"""Pure validation and SQL construction for the read-only tool contracts."""

import math
from collections.abc import Sequence

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import Boolean, Float, Integer, Numeric, String, Table, and_, func, or_, select
from sqlalchemy.sql import ColumnElement, Select

from .errors import GatewayError
from .metadata import validate_column
from .models import Filter, FilterGroup, Metric, Sort


def parse_filter(raw: dict | None) -> Filter | None:
    """Bound the input tree before recursively parsing the strict models.

    Args:
        raw (dict | None): A condition or nested and/or group; None omits filtering.

    Returns:
        Filter | None: Validated filter with at most five group levels, 30
        conditions and 100 values in each in-list, or None.

    Raises:
        GatewayError: With INVALID_FILTER for malformed or oversized input.
    """
    if raw is None:
        return None
    leaves = 0

    def visit(node: object, depth: int) -> None:
        nonlocal leaves
        if not isinstance(node, dict):
            raise GatewayError("INVALID_FILTER", "Expected a filter object.")
        if "conditions" in node:
            if depth >= 5:
                raise GatewayError("INVALID_FILTER", "At most five group levels are allowed.")
            children = node["conditions"]
            if not isinstance(children, list) or not 1 <= len(children) <= 30:
                raise GatewayError("INVALID_FILTER", "Groups require 1 to 30 children.")
            for child in children:
                visit(child, depth + 1)
        else:
            leaves += 1
            if leaves > 30:
                raise GatewayError("INVALID_FILTER", "At most 30 conditions are allowed.")

    visit(raw, 0)
    try:
        return TypeAdapter(Filter).validate_python(raw)
    except ValidationError:
        raise GatewayError("INVALID_FILTER", "Invalid filter structure or values.") from None


def _compatible(value: object, column_type: object) -> bool:
    if isinstance(column_type, Boolean):
        return type(value) is bool
    if isinstance(column_type, Integer):
        return type(value) is int
    if isinstance(column_type, (Float, Numeric)):
        return type(value) in {int, float} and math.isfinite(value)
    if isinstance(column_type, String):
        return type(value) is str
    return False


def build_filter_expression(table: Table, where: Filter | None) -> ColumnElement[bool] | None:
    """Translate a bounded filter into bound expressions and literal text searches.

    Args:
        table (Table): Reflected, approved table whose types validate filter values.
        where (Filter | None): Filter already bounded by parse_filter, or None.

    Returns:
        ColumnElement[bool] | None: Predicate with bound values, or None.

    Raises:
        GatewayError: For unknown columns or incompatible operators and values.
    """
    if where is None:
        return None
    if isinstance(where, FilterGroup):
        expressions = [build_filter_expression(table, item) for item in where.conditions]
        return (and_ if where.logic == "and" else or_)(*expressions)
    validate_column(table.name, where.column)
    column = table.c[where.column]
    operator = where.operator
    if operator == "is_null":
        return column.is_(None)
    if operator == "is_not_null":
        return column.is_not(None)
    values = where.value if operator == "in" else [where.value]
    if not isinstance(values, list) or not all(_compatible(v, column.type) for v in values):
        raise GatewayError("INVALID_FILTER", "Filter value is incompatible with the column type.")
    if operator == "contains":
        if not isinstance(column.type, String):
            raise GatewayError("INVALID_FILTER", "contains requires a text column.")
        return column.contains(where.value, autoescape=True)
    if operator == "in":
        return column.in_(values)
    if isinstance(column.type, Boolean) and operator not in {"eq", "ne"}:
        raise GatewayError("INVALID_FILTER", "Boolean columns support equality and NULL checks.")
    operations = {
        "eq": column.__eq__,
        "ne": column.__ne__,
        "gt": column.__gt__,
        "gte": column.__ge__,
        "lt": column.__lt__,
        "lte": column.__le__,
    }
    return operations[operator](where.value)


def validate_columns(table: Table, columns: Sequence[str], *, allow_empty: bool = False) -> None:
    """Check the approved identifiers and reject duplicate selections.

    Args:
        table (Table): Approved source table.
        columns (Sequence[str]): Column names to validate.
        allow_empty (bool): Whether an empty selection is valid, as for grouping.

    Raises:
        GatewayError: For empty, duplicate or unapproved column names.
    """
    if (not columns and not allow_empty) or len(set(columns)) != len(columns):
        raise GatewayError("INVALID_ARGUMENT", "Columns must be nonempty and unique.")
    for name in columns:
        validate_column(table.name, name)


def validate_select(table: Table, columns: list[str], order_by: list[Sort]) -> None:
    """Validate projection and ordering before constructing a SELECT.

    Args:
        table (Table): Approved reflected source table.
        columns (list[str]): Nonempty, unique approved projection names.
        order_by (list[Sort]): Ordering keys; approved unprojected columns are allowed.

    Raises:
        GatewayError: For invalid projection or ordering identifiers.
    """
    validate_columns(table, columns)
    for sort in order_by:
        validate_column(table.name, sort.column)


def metric_name(metric: Metric) -> str:
    """Return the stable output name used for both projection and ordering.

    Args:
        metric (Metric): Metric with an optional explicit alias.

    Returns:
        str: Explicit alias, or function_column such as avg_survived or count_all.
    """
    return metric.alias or f"{metric.function}_{metric.column or 'all'}"


def validate_aggregation(
    table: Table, metrics: list[Metric], group_by: list[str], order_by: list[Sort]
) -> None:
    """Validate metric compatibility, unique result names and aggregate ordering.

    Args:
        table (Table): Approved reflected source table.
        metrics (list[Metric]): Nonempty metric selection with optional aliases.
        group_by (list[str]): Unique approved grouping columns, possibly empty.
        order_by (list[Sort]): Keys naming only groups or metric output names.

    Raises:
        GatewayError: For invalid columns, metrics, name collisions or sort keys.
    """
    validate_columns(table, group_by, allow_empty=True)
    if not metrics:
        raise GatewayError("INVALID_AGGREGATION", "At least one metric is required.")
    names = set(group_by)
    for metric in metrics:
        if metric.column is None and metric.function != "count":
            raise GatewayError("INVALID_AGGREGATION", "This metric requires a column.")
        if metric.column is not None:
            validate_column(table.name, metric.column)
            kind = table.c[metric.column].type
            if metric.function in {"sum", "avg"} and not isinstance(
                kind, (Integer, Float, Numeric)
            ):
                raise GatewayError("INVALID_AGGREGATION", "sum and avg require numeric columns.")
            if metric.function in {"min", "max"} and not isinstance(
                kind, (Integer, Float, Numeric, String)
            ):
                raise GatewayError("INVALID_AGGREGATION", "min and max require comparable columns.")
        name = metric_name(metric)
        if name in names:
            raise GatewayError(
                "INVALID_AGGREGATION", "Metric names must be unique and disjoint from groups."
            )
        names.add(name)
    if any(sort.column not in names for sort in order_by):
        raise GatewayError("INVALID_AGGREGATION", "Sort keys must name groups or output metrics.")


def build_select_statement(
    table: Table,
    columns: list[str],
    where: ColumnElement[bool] | None,
    order_by: list[Sort],
    limit: int,
) -> Select:
    """Construct a bounded projection without executing SQL.

    Args:
        table (Table): Approved reflected source table.
        columns (list[str]): Projection in requested order, checked by validate_select.
        where (ColumnElement[bool] | None): Compiled filter, or None to omit WHERE.
        order_by (list[Sort]): Validated ascending/descending table-column sort keys.
        limit (int): Validated maximum row count between 1 and 200.

    Returns:
        Select: Core statement projecting exactly the requested columns, with
        optional filtering and ordering and an enforced limit; no pagination.
    """
    stmt = select(*[table.c[col] for col in columns]).select_from(table)
    if where is not None:
        stmt = stmt.where(where)
    for sort in order_by:
        column = table.c[sort.column]
        stmt = stmt.order_by(column.asc() if sort.direction == "asc" else column.desc())
    stmt = stmt.limit(limit)

    return stmt


def build_aggregate_statement(
    table: Table,
    metrics: list[Metric],
    group_by: list[str],
    where: ColumnElement[bool] | None,
    order_by: list[Sort],
    limit: int,
) -> Select:
    """Construct a bounded aggregate query without executing SQL.

    Args:
        table (Table): Approved reflected source table.
        metrics (list[Metric]): Metrics checked by validate_aggregation. count with
            no column means COUNT(*); other metrics operate on their named column.
        group_by (list[str]): Validated grouping columns in output order.
        where (ColumnElement[bool] | None): Compiled filter applied before grouping.
        order_by (list[Sort]): Validated keys naming groups or metric output names.
        limit (int): Validated maximum result row count between 1 and 200.

    Returns:
        Select: Core statement projecting groups followed by labelled metrics,
        with explicit FROM, optional WHERE/GROUP BY/ordering and a limit.
    """
    stmt = select(*[table.c[col] for col in group_by]).select_from(table)

    for metric in metrics:
        if metric.function == "count" and metric.column is None:
            stmt = stmt.add_columns(func.count().label(metric_name(metric)))
        else:
            column = table.c[metric.column]
            func_map = {
                "count": func.count,
                "sum": func.sum,
                "avg": func.avg,
                "min": func.min,
                "max": func.max,
            }
            stmt = stmt.add_columns(func_map[metric.function](column).label(metric_name(metric)))
    if where is not None:
        stmt = stmt.where(where)
    if group_by:
        stmt = stmt.group_by(*[table.c[col] for col in group_by])
    for sort in order_by:
        column = stmt.selected_columns[sort.column]
        stmt = stmt.order_by(column.asc() if sort.direction == "asc" else column.desc())
    stmt = stmt.limit(limit)

    return stmt
