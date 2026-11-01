"""Validate local runtime configuration without opening a database."""

import os
from pathlib import Path

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

from .errors import GatewayError


class Config:
    """Runtime settings validated from the process environment.

    Attributes:
        database_path (Path): Existing SQLite file resolved from the required URL.
        host (str): Loopback bind host, defaulting to 127.0.0.1.
        port (int): Bind port in 1-65535, defaulting to 8000.
    """

    def __init__(self) -> None:
        """Read and validate MCP_DATA_GW_DATABASE_URL, HOST and PORT settings.

        Raises:
            GatewayError: With INVALID_ARGUMENT for absent or invalid configuration.
        """
        try:
            url = make_url(os.environ.get("MCP_DATA_GW_DATABASE_URL", ""))
            if (
                url.drivername not in {"sqlite", "sqlite+pysqlite"}
                or not url.database
                or url.database == ":memory:"
                or url.host
                or url.username
                or url.password
                or url.query
            ):
                raise ValueError
            self.database_path = Path(url.database).resolve()
            if not self.database_path.is_file():
                raise ValueError
            self.host = os.environ.get("MCP_DATA_GW_HOST", "127.0.0.1")
            if self.host not in {"127.0.0.1", "localhost", "::1", "0.0.0.0"}:
                raise ValueError
            self.port = int(os.environ.get("MCP_DATA_GW_PORT", "8000"))
            if not 1 <= self.port <= 65535:
                raise ValueError
        except (ArgumentError, ValueError, OSError):
            raise GatewayError(
                "INVALID_ARGUMENT",
                "Configure an existing SQLite file URL, a loopback host and a port in 1-65535.",
            ) from None
