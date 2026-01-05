import asyncio
import socket
import threading
import time
import weakref
from typing import Any
from proxycraft import ProxyCraft
from proxycraft.config.models import Config
import json
import httpx

from pycontainer.utils import _build_command_line, get_exit_code, clean_result
import nest_asyncio

from pycontainer.logger import get_logger

nest_asyncio.apply()

logger = get_logger(__name__)

CONFIGURATION = {
    "version": "1.0",
    "name": "PyContainer",
    "server": {
        "type": "local"
    },
    "endpoints": [
        {
            "backends": {
                "command": {
                    "darwin": "docker",
                    "default": "docker",
                    "id": "docker"
                }
            },
            "identifier": "/docker",
            "match": "/docker/**",
            "prefix": "/docker",
            "upstream": {
                "proxy": {
                    "enabled": True
                }
            }
        }
    ]
}


class Container:

    def __init__(self, parent, data: dict[str, Any] | None = None, **kwargs):
        """
        Initialize container with data from dict or kwargs

        Args:
            data: Dictionary to convert to attributes
            **kwargs: Additional keyword arguments to set as attributes
        """
        self.parent = parent

        if data is not None:
            # If data is provided, use it
            for key, value in data.items():
                self._set_attribute(key, value)

        # Override with any kwargs
        for key, value in kwargs.items():
            self._set_attribute(key, value)

    def _set_attribute(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def __str__(self) -> str:
        """User-friendly string representation"""
        return self.__repr__()

    def __getattr__(self, command: str, *args, **kwargs) -> Any:
        def command_wrapper(*args, **kwargs):
            full_command_args = _build_command_line(f"{command if command != 'execute' else 'exec'} {self.ID}", *args,
                                                    **kwargs)

            result, command_status = asyncio.run(
                self.parent._execute_request(full_command_args=full_command_args)
            )
            exit_code = get_exit_code(result)
            result_cleaned = clean_result(result)

            if exit_code > 0:
                raise ValueError(result_cleaned)

            return result_cleaned

        return command_wrapper


class PyContainer:
    async def _session_client(self, app, method, payload, stream):
        transport = httpx.ASGITransport(app=app)

        async with httpx.AsyncClient(
                transport=transport, base_url="http://pycontainer"
        ) as client:
            if stream:
                async with client.stream(
                        url="/docker",
                        method=method,
                        json=payload,
                ) as response:
                    response.raise_for_status()
                    yield response
            else:
                response = await client.request(
                    url="/docker",
                    method=method,
                    json=payload,
                )
                response.raise_for_status()
                yield response

    def __getattr__(self, command: str):
        """Handle any method call dynamically."""

        def command_wrapper(*args, **kwargs):
            full_command_args = _build_command_line(command, *args, **kwargs)
            result, command_status = asyncio.run(
                self._execute_request(full_command_args=full_command_args)
            )
            exit_code = get_exit_code(result)
            result_cleaned = clean_result(result)


            if exit_code > 0:
                raise ValueError(result)

            if command == "run":
                return Container(parent=self, ID=result_cleaned.replace('\r\n\n', ''))

            if command == "ps":
                # return a list of containers
                containers = []
                for row in result_cleaned.split("\n"):
                    if row != "":
                        row_json = json.loads(row)
                        containers.append(Container(parent=self, **row_json))
                return containers
            return result_cleaned.replace('\r\n\n', '')

        return command_wrapper

    async def _execute_request(self, full_command_args: str) -> Any:
        # curl -X POST https://localhost -H "Content-Type: application/json" -d '{"args": ["ls"]}' -k

        logger.debug(f"command args : {full_command_args}")
        async for response in self._session_client(
                app=self.proxycraft.app,
                method="GET",
                stream=False,
                payload={"args": full_command_args},
        ):
            return response.text, response.status_code
        return None

    def __init__(
            self,
            debug: bool = False,
    ):
        # Initialize the proxy
        self.proxycraft: ProxyCraft = ProxyCraft(config=Config(**CONFIGURATION))

        # Start proxy in a separate daemon thread
        self.proxy_thread = threading.Thread(
            target=self.proxycraft.serve, daemon=True, name="ProxyCraftThread"
        )
        self._initialized = False
        try:
            self.loop = asyncio.get_running_loop()
            self.startup_task = asyncio.create_task(self.proxycraft.startup_event())

            logger.debug("We're in an asyncio context")
        except RuntimeError:
            logger.debug("We're NOT in an asyncio context")
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.proxycraft.startup_event())

        self.transport = httpx.ASGITransport(app=self.proxycraft.app)
        weakref.finalize(self, self._cleanup_sync, self.proxycraft, self.loop)

        def wait_port_available(host: str, port: int):
            def _socket_test_connection():
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(1)  # Add timeout to avoid blocking indefinitely
                    result = s.connect_ex((host, port))
                    s.close()
                    return result == 0  # 0 means connection successful
                except Exception:
                    return False

            while _socket_test_connection():
                logger.info(f"waiting for port {port}")
                time.sleep(1)

        def check_port_available(host: str, port: int):
            def _socket_test_connection():
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(1)  # Add timeout to avoid blocking indefinitely
                    result = s.connect_ex((host, port))
                    s.close()
                    return result == 1
                except Exception:
                    return True

            while _socket_test_connection():
                logger.info(f"port {port} is not available")
                time.sleep(1)

        check_port_available(host="0.0.0.0", port=8080)
        self.proxy_thread.start()
        wait_port_available(host="0.0.0.0", port=8080)

    async def close(self):
        """Async cleanup method"""
        await self.proxycraft.shutdown_event()

    def __del__(self):
        """Synchronous cleanup - calls async close() properly"""
        try:
            # Try to get the current running loop
            current_loop = asyncio.get_running_loop()
            # If we're in an async context, schedule the cleanup
            current_loop.create_task(self.close())
        except RuntimeError:
            # No running loop, check if we have our own loop
            if hasattr(self, "loop") and self.loop and not self.loop.is_closed():
                # Use our own loop
                asyncio.set_event_loop(self.loop)
                try:
                    self.loop.run_until_complete(self.close())
                finally:
                    self.loop.close()
            else:
                # Last resort: create new event loop
                try:
                    asyncio.run(self.close())
                except Exception:
                    ...
                    # If all else fails, at least log the issue
                    # print("Warning: Could not properly close async resources")
        if hasattr(self, "proxy_thread"):
            self.proxy_thread.join(timeout=1)
            # del self.proxycraft

    @staticmethod
    def _cleanup_sync(proxy: Any, loop: asyncio.AbstractEventLoop):
        """Static cleanup method for weakref.finalize"""
        if loop and not loop.is_closed():
            try:
                asyncio.set_event_loop(loop)
                loop.run_until_complete(proxy.shutdown_event())
                loop.close()
            except Exception as e:
                print(f"Warning: Cleanup failed: {e}")
