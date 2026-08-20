"""Unit evidence for the bounded S10-01 Qwen adapter."""

import json

import httpx

from app.infrastructure.qwen_communication import (
    QwenCommunicationAdapter,
    QwenCommunicationUnavailable,
    QwenCommunicationValidation,
)

FACTS = {
    "full_name": "候选人甲",
    "skills": ["Python", "FastAPI"],
    "work_experience": [{"title": "后端工程师", "company_name": "示例公司"}],
    "project_experience": [{"name": "招聘助手", "technologies": ["FastAPI"]}],
}


def response(content: dict[str, object], status_code: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code,
        json={"choices": [{"message": {"content": json.dumps(content, ensure_ascii=False)}}]},
    )


def test_qwen_adapter_sends_only_structured_facts() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return response({"supported": True, "answer": "候选人使用过 Python。", "fact_refs": ["Python"]})

    adapter = QwenCommunicationAdapter(
        api_key="test-key",
        base_url="https://qwen.test/v1",
        model="qwen-plus",
        transport=httpx.MockTransport(handler),
    )

    import asyncio

    result = asyncio.run(adapter.answer(question="候选人使用过什么语言？", facts=FACTS))

    assert result.supported is True
    body = json.loads(requests[0].content)
    user_content = json.loads(body["messages"][1]["content"])
    assert user_content["facts"] == FACTS
    assert "resume.pdf" not in json.dumps(body)
    assert "C:\\" not in json.dumps(body)


def test_qwen_adapter_retries_provider_failure() -> None:
    attempts = 0

    async def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(503)

    adapter = QwenCommunicationAdapter(
        api_key="test-key",
        base_url="https://qwen.test/v1",
        model="qwen-plus",
        max_retries=2,
        transport=httpx.MockTransport(handler),
    )

    import asyncio

    try:
        asyncio.run(adapter.answer(question="问题", facts=FACTS))
    except QwenCommunicationUnavailable:
        pass
    else:
        raise AssertionError("provider failure must be classified")
    assert attempts == 3


def test_qwen_adapter_rejects_unstructured_output() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return response({"supported": True, "answer": "没有 fact refs", "unexpected": "raw"})

    adapter = QwenCommunicationAdapter(
        api_key="test-key",
        base_url="https://qwen.test/v1",
        model="qwen-plus",
        transport=httpx.MockTransport(handler),
    )

    import asyncio

    try:
        asyncio.run(adapter.answer(question="问题", facts=FACTS))
    except QwenCommunicationValidation:
        pass
    else:
        raise AssertionError("unstructured output must be rejected")


def test_qwen_adapter_without_credentials_is_controlled_failure() -> None:
    adapter = QwenCommunicationAdapter(
        api_key=None,
        base_url="https://qwen.test/v1",
        model="qwen-plus",
    )

    import asyncio

    try:
        asyncio.run(adapter.answer(question="问题", facts=FACTS))
    except QwenCommunicationUnavailable:
        pass
    else:
        raise AssertionError("missing credentials must be classified")
