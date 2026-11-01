"""Read-only SQLite connections and the mockable database boundary."""

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from time import monotonic

from sqlalchemy import MetaData, Table, create_engine, inspect
from sqlalchemy.engine import Connection
from sqlalchemy.sql import Select

from .errors import GatewayError
from .metadata import SCHEMA, validate_table


class Database:
    """Reflect and query an existing file; never create or modify the database."""

    def __init__(self, path: Path) -> None:
        """Configure a lazy engine that can only open an existing file read-only.

        Args:
            path (Path): SQLite file path; opening is deferred until a query.
        """
        uri = path.resolve().as_uri() + "?mode=ro"
        self.engine = create_engine(
            "sqlite://",
            creator=lambda: sqlite3.connect(uri, uri=True, timeout=5, check_same_thread=False),
            hide_parameters=True,
        )

    @contextmanager
    def _connection(self) -> Generator[Connection]:
        """Release the connection and progress handler even when a query fails."""
        with self.engine.connect() as connection:
            driver = connection.connection.driver_connection
            deadline = monotonic() + 5
            driver.set_progress_handler(lambda: int(monotonic() > deadline), 1000)
            try:
                yield connection
            finally:
                driver.set_progress_handler(None, 0)

    def list_tables(self) -> list[str]:
        """Return alphabetically sorted approved table names present in the database.

        Returns:
            list[str]: Existing approved names, possibly empty.
        """
        with self._connection() as connection:
            return sorted(set(inspect(connection).get_table_names()) & SCHEMA.keys())

    def reflect(self, name: str) -> Table:
        """Read actual schema metadata without inventing keys or following references.

        Args:
            name (str): Exact approved table name.

        Returns:
            Table: Reflected Core table with actual declared column metadata.

        Raises:
            GatewayError: If the table is unapproved, absent or lacks required columns.
        """
        validate_table(name)
        with self._connection() as connection:
            if name not in inspect(connection).get_table_names():
                raise GatewayError(
                    "TABLE_NOT_FOUND", "Approved table is missing from the database."
                )
            table = Table(name, MetaData(), autoload_with=connection, resolve_fks=False)
        if not set(SCHEMA[name]).issubset(table.c.keys()):
            raise GatewayError(
                "DATABASE_UNAVAILABLE", "Database schema does not match the approved structure."
            )
        return table

    def foreign_keys(self, name: str) -> list[dict]:
        """Read declared foreign keys separately from semantic relationships.

        Args:
            name (str): Exact approved table name.

        Returns:
            list[dict]: Inspector records; empty for the prescribed reference schema.
        """
        validate_table(name)
        with self._connection() as connection:
            return [dict(item) for item in inspect(connection).get_foreign_keys(name)]

    def execute(self, statement: Select) -> list[dict]:
        """Execute a server-constructed, bounded read statement.

        Args:
            statement (Select): Validated Core SELECT with a server-enforced limit.

        Returns:
            list[dict]: Result mappings with native values; possibly empty.
        """
        with self._connection() as connection:
            return [dict(row) for row in connection.execute(statement).mappings()]

    def close(self) -> None:
        """Dispose of pooled database connections."""
        self.engine.dispose()
