"""Official MCP SDK handlers with typed results and sanitized tool errors."""

import json
import logging
from collections.abc import Callable
from contextlib import asynccontextmanager
from uuid import uuid4

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from sqlalchemy.exc import SQLAlchemyError

from .errors import GatewayError
from .logging import keep_mcp_response
from .models import DescriptionResult, Filter, Limit, Metric, RowsResult, Sort, TablesResult
from .service import Service

logger = logging.getLogger(__name__)


def _call[T](operation: Callable[[], T]) -> T:
    try:
        return operation()
    except GatewayError as error:
        raise ToolError(str(error)) from None
    except Exception as error:
        event_id = uuid4().hex
        logger.error(
            json.dumps(
                {
                    "event": "tool_failure",
                    "event_id": event_id,
                    "error_type": type(error).__name__,
                }
            )
        )
        code = "DATABASE_UNAVAILABLE" if isinstance(error, SQLAlchemyError) else "INTERNAL_ERROR"
        raise ToolError(f"[{code}] Request failed; reference {event_id}.") from None


def create_server(service: Service) -> MCPServer:
    """Register the read-only MCP tools and database-cleanup lifecycle.

    Args:
        service (Service): Application service with an existing database boundary.

    Returns:
        MCPServer: Server ready for in-memory clients or Streamable HTTP startup.
    """

    @asynccontextmanager
    async def lifespan(server: MCPServer):
        try:
            yield {}
        finally:
            service.database.close()

    mcp = MCPServer("mcp-data-gw", lifespan=lifespan)

    @mcp.tool(
        title="List Titanic tables",
        annotations=ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
            open_world_hint=False,
            idempotent_hint=True,
        ),
    )
    @keep_mcp_response
    def list_tables() -> TablesResult:
        """Discover the approved Titanic tables available for read-only queries.

        Returns:
            TablesResult: Alphabetically sorted tables with name and description.
            Only Alive, Class, Deck, EmbarkTown, Embarked, Observation, Sex and Who
            are eligible. An empty tables list is a successful result.

        Raises:
            ToolError: A controlled error if database discovery is unavailable.
        """
        return _call(service.list_tables)

    @mcp.tool(
        title="Describe a Titanic table",
        annotations=ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
            open_world_hint=False,
            idempotent_hint=True,
        ),
    )
    @keep_mcp_response
    def describe_table(table: str) -> DescriptionResult:
        """Inspect a table's schema and meaning before constructing a query.

        Args:
            table (str): Exact approved table name, such as Observation.

        Returns:
            DescriptionResult: Technical column types, nullability and primary-key
            flags, actual declared foreign keys, separate logical relationships,
            and semantic descriptions. Observation includes current lookup IDs
            and labels, read fresh and sorted by ID; never assume fixed IDs.
            Logical relationships do not assert database constraints.

        Raises:
            ToolError: For an unknown table, unavailable schema or lookup with
                more than 200 rows. Client-visible messages contain error codes.
        """
        return _call(lambda: service.describe_table(table))

    @mcp.tool(
        title="Select Titanic rows",
        annotations=ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
            open_world_hint=False,
            idempotent_hint=True,
        ),
    )
    @keep_mcp_response
    def select_rows(
        table: str,
        columns: list[str],
        where: Filter | None = None,
        order_by: list[Sort] | None = None,
        limit: Limit = 50,
    ) -> RowsResult:
        """Read a bounded projection from one approved Titanic table.

        Args:
            table (str): Exact approved table name; discover with list_tables.
            columns (list[str]): Nonempty unique column names; inspect with describe_table.
            where (Filter | None): Optional condition with column,
                operator and value, or group with logic (and/or) and conditions.
                Operators: eq, ne, gt, gte, lt, lte, in, is_null, is_not_null,
                contains. NULL operators omit value; other values must match
                column types and must not be null. in takes 1-100 values;
                contains searches literal text, including percent/underscore.
                At most five group levels and 30 conditions are allowed.
            order_by (list[Sort] | None): Optional column/direction objects, with
                direction asc or desc. Approved unprojected columns may be used.
            limit (int): Maximum returned rows, 1-200; default 50.

        Returns:
            RowsResult: rows contains exactly the requested columns as native JSON
            values. returned_count counts this response, not all matching rows.
            Empty rows is successful. No pagination or guaranteed tie ordering.

        Raises:
            ToolError: For invalid identifiers, filters, limits or database failures.
        """
        return _call(
            lambda: service.select_rows(
                table,
                columns,
                where.model_dump(exclude_unset=True) if where is not None else None,
                order_by,
                limit,
            )
        )

    @mcp.tool(
        title="Aggregate Titanic rows",
        annotations=ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
            open_world_hint=False,
            idempotent_hint=True,
        ),
    )
    @keep_mcp_response
    def aggregate_rows(
        table: str,
        metrics: list[Metric],
        where: Filter | None = None,
        group_by: list[str] | None = None,
        order_by: list[Sort] | None = None,
        limit: Limit = 50,
    ) -> RowsResult:
        """Compute bounded metrics and optional groups from one approved table.

        Args:
            table (str): Exact approved table name; discover with list_tables.
            metrics (list[Metric]): Nonempty list with function (count/sum/avg/min/max),
                optional column and optional alias. count without column counts
                all rows; count with column counts non-null values. Other functions
                require a column; sum/avg require numeric columns. Aliases must be
                unique, differ from group names, match [A-Za-z_][A-Za-z0-9_]* and
                contain at most 64 characters. Defaults include count_all and avg_age.
            where (Filter | None): Optional pre-aggregation filter using
                the select_rows condition/group format. Maximum five group levels,
                30 conditions and 100 in-values. NULL operators omit value;
                contains searches literal text rather than LIKE patterns.
            group_by (list[str] | None): Optional unique approved grouping columns.
            order_by (list[Sort] | None): Optional asc/desc sort keys naming only
                grouping columns or metric output names, including generated names.
            limit (int): Maximum returned result rows, 1-200; default 50.

        Returns:
            RowsResult: rows contains grouping columns and named metrics as native
            JSON values. returned_count counts this response, not source rows.
            No joins, HAVING, pagination or guaranteed ordering of tied rows.

        Raises:
            ToolError: For invalid identifiers, metrics, filters, limits or DB failures.
        """
        return _call(
            lambda: service.aggregate_rows(
                table,
                metrics,
                where.model_dump(exclude_unset=True) if where is not None else None,
                group_by,
                order_by,
                limit,
            )
        )

    return mcp
