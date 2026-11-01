"""Transport-independent read services and live semantic lookup enrichment."""

from pydantic import TypeAdapter
from sqlalchemy import select

from . import queries
from .database import Database
from .errors import GatewayError
from .metadata import COLUMN_DESCRIPTIONS, DESCRIPTIONS, LOOKUPS, SCHEMA
from .models import (
    ColumnInfo,
    DescriptionResult,
    Limit,
    LookupInfo,
    LookupValue,
    Metric,
    Relationship,
    RowsResult,
    Sort,
    TableEntry,
    TablesResult,
)


class Service:
    """Validate read requests and enrich database metadata with domain meaning."""

    def __init__(self, database: Database) -> None:
        """Initialize the application boundary.

        Args:
            database (Database): Read-only repository used for reflection and execution.
        """
        self.database = database

    def list_tables(self) -> TablesResult:
        """Discover existing approved tables.

        Returns:
            TablesResult: Alphabetically sorted names with semantic descriptions.
        """
        names = sorted(set(self.database.list_tables()) & SCHEMA.keys())
        return TablesResult(tables=[TableEntry(name=n, description=DESCRIPTIONS[n]) for n in names])

    def describe_table(self, name: str) -> DescriptionResult:
        """Combine actual schema metadata with separate live semantic context.

        Args:
            name (str): Exact approved table name.

        Returns:
            DescriptionResult: Columns, declared constraints, logical references
            and fresh lookup values sorted by ID.

        Raises:
            GatewayError: For invalid tables, schemas or lookups exceeding 200 rows.
        """
        table = self.database.reflect(name)
        relationships = []
        lookups = []
        if name == "Observation":
            for target, (key, label) in LOOKUPS.items():
                lookup = self.database.reflect(target)
                values = self.database.execute(
                    select(lookup.c[key], lookup.c[label]).order_by(lookup.c[key]).limit(201)
                )
                if len(values) > 200:
                    raise GatewayError(
                        "DATABASE_UNAVAILABLE", "Lookup exceeds the 200-row safety limit."
                    )
                relationships.append(Relationship(from_column=key, to_table=target, to_column=key))
                lookups.append(
                    LookupInfo(
                        from_column=key,
                        table=target,
                        id_column=key,
                        label_column=label,
                        values=[LookupValue(id=row[key], label=row[label]) for row in values],
                    )
                )
        return DescriptionResult(
            table=name,
            description=DESCRIPTIONS[name],
            columns=[
                ColumnInfo(
                    name=column.name,
                    type=str(column.type),
                    nullable=column.nullable,
                    primary_key=column.primary_key,
                    description=COLUMN_DESCRIPTIONS.get(
                        column.name, "Lookup label from the source dataset"
                    ),
                )
                for column in table.c
                if column.name in SCHEMA[name]
            ],
            declared_foreign_keys=self.database.foreign_keys(name),
            logical_relationships=relationships,
            lookup_values=lookups,
        )

    def select_rows(
        self,
        table: str,
        columns: list[str],
        where: dict | None = None,
        order_by: list[Sort] | None = None,
        limit: int = 50,
    ) -> RowsResult:
        """Validate and execute a bounded projection from one approved table.

        Args:
            table (str): Exact approved table name.
            columns (list[str]): Unique nonempty projection names.
            where (dict | None): Optional raw condition or nested and/or group.
            order_by (list[Sort] | None): Optional validated sort directions and columns.
            limit (int): Maximum returned rows, 1-200; default 50.

        Returns:
            RowsResult: Native result mappings and the count of this response.

        Raises:
            GatewayError: For invalid identifiers, filters or limits.
        """
        limit = self._limit(limit)
        reflected = self.database.reflect(table)
        sorts = order_by or []
        queries.validate_select(reflected, columns, sorts)
        expression = queries.build_filter_expression(reflected, queries.parse_filter(where))
        statement = queries.build_select_statement(reflected, columns, expression, sorts, limit)
        rows = self.database.execute(statement)
        return RowsResult(rows=rows, returned_count=len(rows))

    def aggregate_rows(
        self,
        table: str,
        metrics: list[Metric],
        where: dict | None = None,
        group_by: list[str] | None = None,
        order_by: list[Sort] | None = None,
        limit: int = 50,
    ) -> RowsResult:
        """Validate and execute bounded metrics with optional grouping.

        Args:
            table (str): Exact approved table name.
            metrics (list[Metric]): Nonempty count/sum/avg/min/max selection.
            where (dict | None): Optional filter applied before aggregation.
            group_by (list[str] | None): Optional unique grouping columns.
            order_by (list[Sort] | None): Optional sort by group or metric output name.
            limit (int): Maximum returned result rows, 1-200; default 50.

        Returns:
            RowsResult: Group/metric mappings and the count of this response.

        Raises:
            GatewayError: For invalid identifiers, metrics, filters or limits.
        """
        limit = self._limit(limit)
        reflected = self.database.reflect(table)
        groups, sorts = group_by or [], order_by or []
        queries.validate_aggregation(reflected, metrics, groups, sorts)
        expression = queries.build_filter_expression(reflected, queries.parse_filter(where))
        statement = queries.build_aggregate_statement(
            reflected, metrics, groups, expression, sorts, limit
        )
        rows = self.database.execute(statement)
        return RowsResult(rows=rows, returned_count=len(rows))

    @staticmethod
    def _limit(value: int) -> int:
        try:
            return TypeAdapter(Limit).validate_python(value)
        except ValueError:
            raise GatewayError(
                "INVALID_ARGUMENT", "Limit must be an integer from 1 to 200."
            ) from None
