"""Controlled MCP clients for the MinerU parsing boundary."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Mapping
from contextlib import ExitStack
from datetime import timedelta
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamablehttp_client

from app.infrastructure.mineru_mcp import (
    MineruTimeoutError,
    MineruUnavailableError,
    MineruUnreadableError,
)


class MineruStdioClient:
    """Start the official local Bridge and invoke its verified parse contract."""

    def __init__(
        self,
        *,
        command: str,
        command_args: tuple[str, ...],
        api_token: str,
        timeout_seconds: float = 25,
    ) -> None:
        self._command = command
        self._command_args = command_args
        self._api_token = api_token
        self._timeout_seconds = timeout_seconds

    async def parse_documents(self, *, file_path: str) -> object:
        """Pass one Worker-created PDF path without exposing Bridge output or stderr."""
        parameters = StdioServerParameters(
            command=self._command,
            args=list(self._command_args),
            env=_bridge_environment(self._api_token),
        )
        stage = "spawn"
        try:
            with ExitStack() as stack:
                errlog = stack.enter_context(open(os.devnull, "w", encoding="utf-8"))
                async with asyncio.timeout(self._timeout_seconds):
                    async with stdio_client(parameters, errlog=errlog) as (reader, writer):
                        async with ClientSession(reader, writer) as session:
                            stage = "initialize"
                            await session.initialize()
                            stage = "list_tools"
                            tools = await session.list_tools()
                            if not any(tool.name == "parse_documents" for tool in tools.tools):
                                raise MineruUnreadableError
                            stage = "call_tool"
                            result = await session.call_tool(
                                "parse_documents",
                                arguments={
                                    "file_sources": [file_path],
                                    "enable_ocr": False,
                                    "output_dir": str(os.path.dirname(file_path)),
                                },
                            )
                            if result.isError:
                                raise MineruUnreadableError
                            if isinstance(result.structuredContent, Mapping):
                                return dict(result.structuredContent)
                            return {"content": [item.model_dump(mode="json") for item in result.content]}
        except MineruUnreadableError:
            raise
        except TimeoutError as exc:
            raise MineruTimeoutError from exc
        except Exception as exc:
            raise MineruUnavailableError(
                diagnostic_stage=stage,
                diagnostic_kind=type(exc).__name__,
            ) from exc


def _bridge_environment(api_token: str) -> dict[str, str]:
    """Provide only runtime essentials plus the MinerU token to the child process."""
    allowed_names = (
        "ALL_PROXY",
        "APPDATA",
        "COMSPEC",
        "CURL_CA_BUNDLE",
        "HOMEDRIVE",
        "HOMEPATH",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "LOCALAPPDATA",
        "NO_PROXY",
        "PATH",
        "PATHEXT",
        "REQUESTS_CA_BUNDLE",
        "SSL_CERT_FILE",
        "SYSTEMDRIVE",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "USERPROFILE",
        "UV_CACHE_DIR",
        "WINDIR",
    )
    environment = {name: os.environ[name] for name in allowed_names if name in os.environ}
    no_proxy_entries = [
        entry.strip() for entry in environment.get("NO_PROXY", "").split(",") if entry.strip()
    ]
    mineru_direct_hosts = ("cdn-mineru.openxlab.org.cn",)
    environment["NO_PROXY"] = ",".join(dict.fromkeys([*no_proxy_entries, *mineru_direct_hosts]))
    environment["MINERU_API_TOKEN"] = api_token
    environment["ENABLE_LOG"] = "false"
    return environment


class MineruStreamableHttpClient:
    """Discover the official tool schema before invoking one controlled parse request."""

    def __init__(self, *, endpoint: str, api_token: str, timeout_seconds: float = 25) -> None:
        self._endpoint = endpoint
        self._api_token = api_token
        self._timeout_seconds = timeout_seconds

    async def parse_documents(self, *, file_path: str) -> object:
        """Call the discovered official parse tool without inventing unsupported arguments."""
        try:
            async with streamablehttp_client(
                self._endpoint,
                headers={"Authorization": f"Bearer {self._api_token}"},
                timeout=timedelta(seconds=self._timeout_seconds),
            ) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    parse_tool = next((tool for tool in tools.tools if tool.name == "parse_documents"), None)
                    if parse_tool is None:
                        raise MineruUnreadableError
                    argument_name = _file_argument_name(parse_tool.inputSchema)
                    argument_value: object = [file_path] if argument_name == "file_sources" else file_path
                    result = await session.call_tool(
                        "parse_documents", arguments={argument_name: argument_value}
                    )
                    if result.isError:
                        raise MineruUnreadableError
                    if isinstance(result.structuredContent, Mapping):
                        return dict(result.structuredContent)
                    return {"content": [item.model_dump(mode="json") for item in result.content]}
        except MineruUnreadableError:
            raise
        except TimeoutError as exc:
            raise MineruTimeoutError from exc
        except Exception as exc:
            raise MineruUnavailableError from exc


def _file_argument_name(schema: Mapping[str, Any]) -> str:
    properties = schema.get("properties")
    if not isinstance(properties, Mapping):
        raise MineruUnreadableError
    for name in ("file_path", "file_sources"):
        if name in properties:
            return name
    raise MineruUnreadableError
