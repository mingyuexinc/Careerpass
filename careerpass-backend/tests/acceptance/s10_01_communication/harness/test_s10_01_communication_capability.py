"""Capability Acceptance for S10-01 using a replaceable, deterministic transport."""

import json

import httpx
import pytest

from app.infrastructure.qwen_communication import QwenCommunicationAdapter


@pytest.mark.capability_acceptance
def test_s10_01_capability_acceptance() -> None:
    facts = {
        "full_name": "候选人甲",
        "skills": ["Python", "FastAPI"],
        "work_experience": [{"title": "后端工程师"}],
        "project_experience": [{"name": "招聘助手"}],
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        supplied = json.loads(payload["messages"][1]["content"])
        assert supplied["facts"] == facts
        question = supplied["question"]
        if question == "你的工作经历中有包括大模型训练吗？":
            answer = {
                "supported": True,
                "answer": "从当前求职资料看，没有大模型训练相关经历。",
                "fact_refs": [],
            }
        else:
            answer = {
                "supported": True,
                "answer": "候选人使用过 Python 和 FastAPI。",
                "fact_refs": ["Python", "FastAPI"],
            }
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(answer, ensure_ascii=False)
                        }
                    }
                ]
            },
        )

    import asyncio

    result = asyncio.run(
        QwenCommunicationAdapter(
            api_key="acceptance-key",
            base_url="https://qwen.test/v1",
            model="qwen-plus",
            transport=httpx.MockTransport(handler),
        ).answer(question="候选人使用过哪些技能？", facts=facts)
    )
    assert result.answer == "候选人使用过 Python 和 FastAPI。"

    negative_result = asyncio.run(
        QwenCommunicationAdapter(
            api_key="acceptance-key",
            base_url="https://qwen.test/v1",
            model="qwen-plus",
            transport=httpx.MockTransport(handler),
        ).answer(question="你的工作经历中有包括大模型训练吗？", facts=facts)
    )
    assert negative_result.supported is True
    assert negative_result.answer == "从当前求职资料看，没有大模型训练相关经历。"
    assert negative_result.fact_refs == []
