"""Unit tests for the restricted environment and protocol of the MinerU stdio Bridge."""

import asyncio
from types import SimpleNamespace

import pytest

from app.infrastructure.mineru_mcp import (
    MineruTimeoutError,
    MineruUnavailableError,
    MineruUnreadableError,
)
from app.infrastructure.mineru_mcp_client import (
    MineruStdioClient,
    MineruStreamableHttpClient,
    _bridge_environment,
    _file_argument_name,
)


class AsyncContext:
    def __init__(self, value: object | None = None, error: Exception | None = None) -> None:
        self.value = value
        self.error = error

    async def __aenter__(self) -> object:
        if self.error is not None:
            raise self.error
        return self.value

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        del exc_type, exc_value, traceback


class FakeSession:
    def __init__(
        self,
        *,
        tool_names: list[str],
        content: list[object],
        structured_content: dict[str, object] | None = None,
        is_error: bool = False,
    ) -> None:
        self._tool_names = tool_names
        self._content = content
        self._structured_content = structured_content
        self._is_error = is_error
        self.arguments: dict[str, object] | None = None
        self.initialized = False

    async def __aenter__(self) -> "FakeSession":
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        del exc_type, exc_value, traceback

    async def initialize(self) -> None:
        self.initialized = True

    async def list_tools(self) -> object:
        return SimpleNamespace(tools=[SimpleNamespace(name=name) for name in self._tool_names])

    async def call_tool(self, name: str, *, arguments: dict[str, object]) -> object:
        assert name == "parse_documents"
        self.arguments = arguments
        return SimpleNamespace(
            content=self._content,
            structuredContent=self._structured_content,
            isError=self._is_error,
        )


class FakeContent:
    def model_dump(self, *, mode: str) -> dict[str, str]:
        assert mode == "json"
        return {"type": "text", "text": "# safe markdown"}


def test_bridge_environment_contains_runtime_essentials_and_mineru_token(monkeypatch) -> None:
    monkeypatch.setenv("PATH", "safe-path")
    monkeypatch.setenv("HTTPS_PROXY", "http://controlled-proxy.invalid")
    monkeypatch.setenv("NO_PROXY", "localhost,127.0.0.1")
    monkeypatch.setenv("MINERU_API_KEY", "ambient-token-must-not-pass-through")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "qwen-token-must-not-pass-through")

    environment = _bridge_environment("mineru-child-token")

    assert environment["PATH"] == "safe-path"
    assert environment["HTTPS_PROXY"] == "http://controlled-proxy.invalid"
    assert environment["NO_PROXY"] == (
        "localhost,127.0.0.1,cdn-mineru.openxlab.org.cn"
    )
    assert environment["MINERU_API_TOKEN"] == "mineru-child-token"
    assert environment["ENABLE_LOG"] == "false"
    assert "MINERU_API_KEY" not in environment
    assert "DASHSCOPE_API_KEY" not in environment


def test_stdio_client_uses_verified_contract_and_suppresses_bridge_stderr(monkeypatch) -> None:
    from app.infrastructure import mineru_mcp_client

    session = FakeSession(tool_names=["parse_documents"], content=[FakeContent()])
    parameters: list[object] = []

    def fake_stdio_client(value, *, errlog):
        parameters.append(value)
        assert errlog is not None
        return AsyncContext((object(), object()))

    monkeypatch.setattr(mineru_mcp_client, "stdio_client", fake_stdio_client)
    monkeypatch.setattr(mineru_mcp_client, "ClientSession", lambda reader, writer: session)
    client = MineruStdioClient(
        command="uvx",
        command_args=("mineru-open-mcp",),
        api_token="test-token",
    )

    result = asyncio.run(client.parse_documents(file_path="C:/controlled/resume.pdf"))

    assert result == {"content": [{"type": "text", "text": "# safe markdown"}]}
    assert session.initialized
    assert session.arguments == {
        "file_sources": ["C:/controlled/resume.pdf"],
        "enable_ocr": False,
        "output_dir": "C:/controlled",
    }
    assert len(parameters) == 1


def test_stdio_client_prefers_structured_tool_result(monkeypatch) -> None:
    from app.infrastructure import mineru_mcp_client

    structured = {
        "status": "success",
        "results": [{"status": "success", "content": "# Resume"}],
    }
    session = FakeSession(
        tool_names=["parse_documents"],
        content=[FakeContent()],
        structured_content=structured,
    )
    monkeypatch.setattr(
        mineru_mcp_client,
        "stdio_client",
        lambda value, *, errlog: AsyncContext((object(), object())),
    )
    monkeypatch.setattr(mineru_mcp_client, "ClientSession", lambda reader, writer: session)

    result = asyncio.run(
        MineruStdioClient(
            command="uvx",
            command_args=("mineru-open-mcp",),
            api_token="test-token",
        ).parse_documents(file_path="C:/controlled/resume.pdf")
    )

    assert result == structured


def test_stdio_client_rejects_missing_parse_tool(monkeypatch) -> None:
    from app.infrastructure import mineru_mcp_client

    session = FakeSession(tool_names=["get_ocr_languages"], content=[])
    monkeypatch.setattr(
        mineru_mcp_client,
        "stdio_client",
        lambda value, *, errlog: AsyncContext((object(), object())),
    )
    monkeypatch.setattr(mineru_mcp_client, "ClientSession", lambda reader, writer: session)
    client = MineruStdioClient(
        command="uvx", command_args=("mineru-open-mcp",), api_token="test-token"
    )

    with pytest.raises(MineruUnreadableError):
        asyncio.run(client.parse_documents(file_path="C:/controlled/resume.pdf"))


@pytest.mark.parametrize(
    ("error", "expected"),
    [(TimeoutError(), MineruTimeoutError), (OSError(), MineruUnavailableError)],
)
def test_stdio_client_classifies_transport_failures(monkeypatch, error, expected) -> None:
    from app.infrastructure import mineru_mcp_client

    monkeypatch.setattr(
        mineru_mcp_client,
        "stdio_client",
        lambda value, *, errlog: AsyncContext(error=error),
    )
    client = MineruStdioClient(
        command="uvx", command_args=("mineru-open-mcp",), api_token="test-token"
    )

    with pytest.raises(expected):
        asyncio.run(client.parse_documents(file_path="C:/controlled/resume.pdf"))


def test_conditional_remote_client_uses_array_for_file_sources(monkeypatch) -> None:
    from app.infrastructure import mineru_mcp_client

    class RemoteSession(FakeSession):
        async def list_tools(self) -> object:
            return SimpleNamespace(
                tools=[
                    SimpleNamespace(
                        name="parse_documents",
                        inputSchema={"properties": {"file_sources": {"type": "array"}}},
                    )
                ]
            )

    session = RemoteSession(tool_names=[], content=[FakeContent()])
    monkeypatch.setattr(
        mineru_mcp_client,
        "streamablehttp_client",
        lambda endpoint, *, headers, timeout: AsyncContext((object(), object(), object())),
    )
    monkeypatch.setattr(mineru_mcp_client, "ClientSession", lambda reader, writer: session)
    client = MineruStreamableHttpClient(endpoint="https://example.invalid/mcp", api_token="test-token")

    result = asyncio.run(client.parse_documents(file_path="C:/controlled/resume.pdf"))

    assert result == {"content": [{"type": "text", "text": "# safe markdown"}]}
    assert session.arguments == {"file_sources": ["C:/controlled/resume.pdf"]}


@pytest.mark.parametrize(
    ("error", "expected"),
    [(TimeoutError(), MineruTimeoutError), (OSError(), MineruUnavailableError)],
)
def test_conditional_remote_client_classifies_transport_failures(monkeypatch, error, expected) -> None:
    from app.infrastructure import mineru_mcp_client

    monkeypatch.setattr(
        mineru_mcp_client,
        "streamablehttp_client",
        lambda endpoint, *, headers, timeout: AsyncContext(error=error),
    )
    client = MineruStreamableHttpClient(endpoint="https://example.invalid/mcp", api_token="test-token")

    with pytest.raises(expected):
        asyncio.run(client.parse_documents(file_path="C:/controlled/resume.pdf"))


def test_remote_schema_helper_rejects_unusable_schema() -> None:
    assert _file_argument_name({"properties": {"file_path": {}}}) == "file_path"
    with pytest.raises(MineruUnreadableError):
        _file_argument_name({"properties": {}})
