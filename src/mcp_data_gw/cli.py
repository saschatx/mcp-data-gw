"""Command-line startup for the local read-only MCP service."""


def main() -> None:
    """Start the local, read-only Streamable HTTP MCP server.

    Load .env without overriding existing variables, validate configuration,
    and serve /mcp with stateless JSON responses and SDK transport protections.
    Database resources are disposed of when the server stops or startup fails.

    Raises:
        SystemExit: With a safe message if runtime configuration is invalid.
    """
    import logging

    from dotenv import load_dotenv

    from .config import Config
    from .database import Database
    from .errors import GatewayError
    from .server import create_server
    from .service import Service

    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        config = Config()
    except GatewayError as error:
        raise SystemExit(str(error)) from None
    database = Database(config.database_path)
    try:
        create_server(Service(database)).run(
            transport="streamable-http",
            host=config.host,
            port=config.port,
            streamable_http_path="/mcp",
            stateless_http=True,
            json_response=True,
        )
    finally:
        database.close()
