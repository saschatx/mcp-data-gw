"""Response logging preserves handler behavior and structured JSON values."""

import asyncio
import inspect
import json

import pytest

from mcp_data_gw import logging as response_logging
from mcp_data_gw.models import RowsResult

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("asynchronous", [False, True])
def test_response_logging_preserves_execution_and_models(tmp_path, monkeypatch, asynchronous):
    path = tmp_path / "responses.jsonl"
    monkeypatch.setattr(response_logging, "MCP_RESPONSE_LOG", path)
    result = RowsResult(rows=[{"age": None, "alone": True}], returned_count=1)

    def handler(limit: int = 1) -> RowsResult:
        return result

    async def async_handler(limit: int = 1) -> RowsResult:
        return result

    original = async_handler if asynchronous else handler
    wrapped = response_logging.keep_mcp_response(original)
    assert inspect.signature(wrapped) == inspect.signature(original)
    assert inspect.iscoroutinefunction(wrapped) is asynchronous
    actual = asyncio.run(wrapped(limit=1)) if asynchronous else wrapped(limit=1)
    assert actual is result
    record = json.loads(path.read_text())
    assert record["response"] == result.model_dump(mode="json")
    assert record["arguments"]["kwargs"] == {"limit": 1}
    assert record["status"] == "ok"


@pytest.mark.parametrize("asynchronous", [False, True])
def test_logged_errors_preserve_exception_without_secret(tmp_path, monkeypatch, asynchronous):
    path = tmp_path / "responses.jsonl"
    monkeypatch.setattr(response_logging, "MCP_RESPONSE_LOG", path)
    error = RuntimeError("password=hidden")

    def handler():
        raise error

    async def async_handler():
        raise error

    wrapped = response_logging.keep_mcp_response(async_handler if asynchronous else handler)
    with pytest.raises(RuntimeError) as caught:
        if asynchronous:
            asyncio.run(wrapped())
        else:
            wrapped()
    assert caught.value is error
    assert json.loads(path.read_text())["status"] == "error"
    assert "password" not in path.read_text()


def test_log_write_failure_does_not_fail_tool(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(response_logging, "MCP_RESPONSE_LOG", tmp_path)

    @response_logging.keep_mcp_response
    def handler() -> int:
        return 42

    assert handler() == 42
    assert "Failed to write MCP response log" in caplog.text
