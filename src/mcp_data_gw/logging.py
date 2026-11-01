import inspect
import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path
from threading import Lock
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)

LOG_DIRECTORY = Path("./logs/").resolve()
ACCESS_LOG = LOG_DIRECTORY / "access.log"
MCP_RESPONSE_LOG = LOG_DIRECTORY / "mcp_responses.jsonl"


def _configure_access_logging() -> None:
    if any(
        isinstance(handler, logging.FileHandler) and Path(handler.baseFilename) == ACCESS_LOG
        for handler in logger.handlers
    ):
        return

    LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(ACCESS_LOG, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def log_access_granted(path: Path) -> None:
    _configure_access_logging()
    logger.info(f"Access granted to file {path}")


def log_access_denied(path: Path) -> None:
    _configure_access_logging()
    logger.warning(f"Access denied to file {path}")


_response_log_lock = Lock()


def _append_lock(record: dict[str, Any]) -> None:
    try:
        line = json.dumps(
            record,
            default=lambda value: (
                value.model_dump(mode="json") if isinstance(value, BaseModel) else str(value)
            ),
            ensure_ascii=False,
        )

        with _response_log_lock:
            MCP_RESPONSE_LOG.parent.mkdir(parents=True, exist_ok=True)
            with MCP_RESPONSE_LOG.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
    except (OSError, TypeError, ValueError):
        # Response logging must not make the tool call fail, but the write
        # failure still needs to be visible to operators.
        logger.error("Failed to write MCP response log")


def keep_mcp_response[**P, T](func: Callable[P, T]) -> Callable[P, T]:
    """Log tool results without changing synchronous or asynchronous execution."""

    def record(timestamp: str, args: tuple, kwargs: dict, **result: Any) -> None:
        _append_lock(
            {
                "timestamp": timestamp,
                "tool": func.__name__,
                "arguments": {"args": args, "kwargs": kwargs},
                **result,
            }
        )

    if inspect.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            timestamp = datetime.now(UTC).isoformat()
            try:
                response = await func(*args, **kwargs)
            except Exception as error:
                record(
                    timestamp, args, kwargs, status="error", error={"type": type(error).__name__}
                )
                raise
            record(timestamp, args, kwargs, status="ok", response=response)
            return response

        return async_wrapper

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        timestamp = datetime.now(UTC).isoformat()
        try:
            response = func(*args, **kwargs)
        except Exception as error:
            record(timestamp, args, kwargs, status="error", error={"type": type(error).__name__})
            raise
        record(timestamp, args, kwargs, status="ok", response=response)
        return response

    return wrapper
