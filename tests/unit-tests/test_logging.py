import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import structlog

from pycontainers import docker
from pycontainers.shared.logging import get_logger, setup_structlog
from pycontainers.shared.runtime.client import PyContainers
from pycontainers.shared.runtime.detection import detect_runtime


def test_detect_runtime_logs_error_when_missing(monkeypatch, capsys):
    monkeypatch.setattr(
        "pycontainers.shared.runtime.detection.shutil.which",
        lambda _name: None,
    )
    with pytest.raises(RuntimeError, match="No container runtime found"):
        detect_runtime()
    captured = capsys.readouterr().out
    assert "No container runtime found on PATH" in captured


def test_cleanup_sync_logs_warning_instead_of_print(capsys):
    loop = asyncio.new_event_loop()
    proxy = MagicMock()
    proxy.shutdown_event = AsyncMock(side_effect=RuntimeError("shutdown failed"))

    PyContainers._cleanup_sync(proxy, loop)

    captured = capsys.readouterr().out
    assert "Runtime client cleanup failed" in captured
    loop.close()


@pytest.mark.asyncio
async def test_execute_request_logs_exception_on_failure(capsys):
    async def failing_session(*args, **kwargs):
        raise ConnectionError("transport down")
        yield  # pragma: no cover

    with patch.object(docker, "_session_client", side_effect=failing_session):
        with pytest.raises(ConnectionError, match="transport down"):
            await docker._execute_request(full_command_args=["ps"])

    captured = capsys.readouterr().out
    assert "Runtime request failed" in captured


def test_setup_structlog_json_mode(caplog):
    setup_structlog(log_level="DEBUG", json_logs=True, include_timestamp=True)
    logger = get_logger("pycontainers.test")
    with caplog.at_level("DEBUG"):
        logger.info("structured json event", key="value")
    assert any("structured json event" in record.message for record in caplog.records)


def test_setup_structlog_console_mode(caplog):
    setup_structlog(log_level="INFO", json_logs=False, include_timestamp=False)
    logger = structlog.get_logger("pycontainers.console")
    with caplog.at_level("INFO"):
        logger.warning("console event")
    assert any("console event" in record.message for record in caplog.records)
