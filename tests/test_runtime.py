"""Runtime configuration and read-only connection setup without opening SQLite."""

import asyncio
from unittest.mock import Mock

import pytest

from mcp_data_gw.config import Config
from mcp_data_gw.database import Database
from mcp_data_gw.errors import GatewayError
from mcp_data_gw.server import create_server

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "url",
    [None, "", "postgresql://user:secret@host/db", "sqlite:///:memory:", "sqlite:///missing.db"],
)
def test_invalid_database_config(monkeypatch, url):
    monkeypatch.delenv("MCP_DATA_GW_DATABASE_URL", raising=False)
    if url is not None:
        monkeypatch.setenv("MCP_DATA_GW_DATABASE_URL", url)
    with pytest.raises(GatewayError, match="INVALID_ARGUMENT") as error:
        Config()
    assert "secret" not in str(error.value)


def test_existing_file_and_local_defaults(monkeypatch):
    monkeypatch.setenv("MCP_DATA_GW_DATABASE_URL", "sqlite:///existing.db")
    monkeypatch.delenv("MCP_DATA_GW_HOST", raising=False)
    monkeypatch.delenv("MCP_DATA_GW_PORT", raising=False)
    monkeypatch.setattr("mcp_data_gw.config.Path.is_file", lambda path: True)
    config = Config()
    assert config.host == "127.0.0.1" and config.port == 8000


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("MCP_DATA_GW_PORT", "0"),
        ("MCP_DATA_GW_PORT", "65536"),
        ("MCP_DATA_GW_PORT", "text"),
        ("MCP_DATA_GW_HOST", "untrusted.example"),
    ],
)
def test_invalid_runtime_settings(monkeypatch, key, value):
    monkeypatch.setenv("MCP_DATA_GW_DATABASE_URL", "sqlite:///existing.db")
    monkeypatch.setattr("mcp_data_gw.config.Path.is_file", lambda path: True)
    monkeypatch.setenv(key, value)
    with pytest.raises(GatewayError):
        Config()


def test_compose_bind_host_is_allowed(monkeypatch):
    monkeypatch.setenv("MCP_DATA_GW_DATABASE_URL", "sqlite:///existing.db")
    monkeypatch.setenv("MCP_DATA_GW_HOST", "0.0.0.0")
    monkeypatch.setattr("mcp_data_gw.config.Path.is_file", lambda path: True)
    assert Config().host == "0.0.0.0"


def test_database_engine_is_lazy_and_forces_read_only_uri(monkeypatch, tmp_path):
    factory = Mock()
    connect = Mock()
    monkeypatch.setattr("mcp_data_gw.database.create_engine", factory)
    monkeypatch.setattr("mcp_data_gw.database.sqlite3.connect", connect)
    path = tmp_path / "not-created.db"
    database = Database(path)
    connect.assert_not_called()
    factory.call_args.kwargs["creator"]()
    assert connect.call_args.args[0].endswith("?mode=ro")
    assert connect.call_args.kwargs["uri"] is True
    assert not path.exists()
    database.close()
    factory.return_value.dispose.assert_called_once()


def test_http_path_and_sdk_protections(service):
    app = create_server(service).streamable_http_app(
        stateless_http=True,
        json_response=True,
        host="127.0.0.1",
    )
    assert any(route.path == "/mcp" for route in app.routes)

    async def scenario():
        async def request(host, origin=None):
            messages = []
            headers = [(b"host", host.encode()), (b"content-type", b"application/json")]
            if origin:
                headers.append((b"origin", origin.encode()))

            async def receive():
                return {"type": "http.request", "body": b"{}", "more_body": False}

            async def send(message):
                messages.append(message)

            await app(
                {
                    "type": "http",
                    "asgi": {"version": "3.0"},
                    "http_version": "1.1",
                    "method": "POST",
                    "scheme": "http",
                    "path": "/mcp",
                    "raw_path": b"/mcp",
                    "root_path": "",
                    "query_string": b"",
                    "headers": headers,
                    "client": ("127.0.0.1", 12345),
                    "server": ("127.0.0.1", 8000),
                },
                receive,
                send,
            )
            return next(
                message["status"]
                for message in messages
                if message["type"] == "http.response.start"
            )

        async with app.router.lifespan_context(app):
            assert await request("untrusted.example") == 421
            assert await request("127.0.0.1:8000", "https://untrusted.example") == 403

    asyncio.run(scenario())


def test_cli_startup_options_and_cleanup(monkeypatch):
    from mcp_data_gw import main

    monkeypatch.setenv("MCP_DATA_GW_DATABASE_URL", "sqlite:///existing.db")
    monkeypatch.delenv("MCP_DATA_GW_HOST", raising=False)
    monkeypatch.delenv("MCP_DATA_GW_PORT", raising=False)
    monkeypatch.setattr("mcp_data_gw.config.Path.is_file", lambda path: True)
    monkeypatch.setattr("dotenv.load_dotenv", lambda: None)
    database_factory = Mock()
    run = Mock()
    monkeypatch.setattr("mcp_data_gw.database.Database", database_factory)
    monkeypatch.setattr("mcp_data_gw.server.MCPServer.run", run)
    main()
    run.assert_called_once_with(
        transport="streamable-http",
        host="127.0.0.1",
        port=8000,
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
    )
    database_factory.return_value.close.assert_called_once()
