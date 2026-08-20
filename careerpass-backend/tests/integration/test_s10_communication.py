"""PostgreSQL verification for the S10-01 Conversation handoff and reply path."""

import asyncio
import os
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, func, select

from app.infrastructure.database import create_database
from app.infrastructure.database.models import (
    AgentRunContext,
    AgentTurn,
    Application,
    Candidate,
    CandidateProfile,
    Conversation,
    HrProfile,
    Job,
    JobGoal,
    Match,
    Message,
    ParsedJobDescriptionSnapshot,
    Resume,
    StoredFileObject,
    User,
)
from app.infrastructure.qwen_communication import QwenCommunicationUnavailable
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.matching_repository import MatchingRepository
from app.schemas.communication import ResumeAnswerDraft
from app.schemas.job_description import ParsedJobDescriptionFields
from app.services.conversation_service import (
    FALLBACK_REPLY,
    NEGATIVE_TRAINING_REPLY,
    ConversationNotFoundError,
    ConversationService,
)

pytestmark = pytest.mark.integration


def _fields(title: str) -> dict[str, object]:
    def text_field(raw: str, order: int) -> dict[str, object]:
        return {
            "raw": raw,
            "normalized": raw,
            "source_heading": "测试",
            "source_order": order,
        }

    return ParsedJobDescriptionFields(
        title=text_field(title, 0),
        company_name=text_field("示例公司", 1),
        location=text_field("上海", 2),
        salary_range={
            "raw": "20-30K",
            "min": 20000,
            "max": 30000,
            "currency": "CNY",
            "period": "month",
            "source_heading": "测试",
            "source_order": 3,
        },
        responsibilities={"raw": "开发", "items": [], "source_heading": "职责", "source_order": 4},
        requirements={"raw": "经验", "items": [], "source_heading": "要求", "source_order": 5},
    ).model_dump(mode="json")


def _database_url() -> str:
    if os.getenv("RUN_INTEGRATION_TESTS") != "true":
        pytest.skip("set RUN_INTEGRATION_TESTS=true after starting the integration compose stack")
    value = os.getenv("TEST_DATABASE_URL")
    if not value:
        pytest.skip("TEST_DATABASE_URL is required for integration tests")
    return value


class FakeResponder:
    def __init__(self, *, delay: float = 0) -> None:
        self.delay = delay
        self.calls = 0
        self.facts: list[dict[str, object]] = []

    async def answer(self, *, question: str, facts: dict[str, object]) -> ResumeAnswerDraft:
        self.calls += 1
        self.facts.append(facts)
        if self.delay:
            await asyncio.sleep(self.delay)
        if question == "provider failure":
            raise QwenCommunicationUnavailable
        if question == "项目经历是什么？":
            return ResumeAnswerDraft(
                supported=True,
                answer="候选人参与过支付平台项目。",
                fact_refs=["支付平台"],
            )
        if question == "并发问题":
            return ResumeAnswerDraft(
                supported=True,
                answer="候选人具备 Python 技能。",
                fact_refs=["Python"],
            )
        return ResumeAnswerDraft(supported=False, answer=FALLBACK_REPLY)


def test_s10_01_postgresql_handoff_authorization_and_idempotency() -> None:
    database_url = _database_url()
    ids = {name: uuid4() for name in (
        "user", "hr_user_two", "candidate", "hr_one", "hr_two", "goal", "run", "profile", "resume",
        "resume_file", "job_file_one", "job_file_two", "job_one", "job_two",
        "snapshot_one", "snapshot_two", "match_one", "match_two",
    )}
    now = datetime.now(UTC)

    async def exercise() -> None:
        database = create_database(database_url)
        try:
            async with database.session_factory() as session:
                session.add_all([
                    User(id=ids["user"], username=f"s10-{ids['user']}", password_hash="test"),
                    User(id=ids["hr_user_two"], username=f"s10-hr-{ids['hr_user_two']}", password_hash="test"),
                    Candidate(id=ids["candidate"], user_id=ids["user"], name="候选人甲"),
                    HrProfile(id=ids["hr_one"], user_id=ids["user"], name="HR 甲"),
                    HrProfile(id=ids["hr_two"], user_id=ids["hr_user_two"], name="HR 乙"),
                    StoredFileObject(
                        id=ids["resume_file"], storage_key=f"s10-resume-{ids['resume_file']}",
                        content_sha256=str(ids["resume_file"]), detected_mime_type="application/pdf",
                        file_size_bytes=1, status="ready",
                    ),
                    StoredFileObject(
                        id=ids["job_file_one"], storage_key=f"s10-job-one-{ids['job_file_one']}",
                        content_sha256=str(ids["job_file_one"]), detected_mime_type="text/markdown",
                        file_size_bytes=1, status="ready",
                    ),
                    StoredFileObject(
                        id=ids["job_file_two"], storage_key=f"s10-job-two-{ids['job_file_two']}",
                        content_sha256=str(ids["job_file_two"]), detected_mime_type="text/markdown",
                        file_size_bytes=1, status="ready",
                    ),
                ])
                await session.flush()
                session.add_all([
                    Resume(
                        id=ids["resume"], candidate_id=ids["candidate"], file_name="resume.pdf",
                        stored_file_object_id=ids["resume_file"], file_type="pdf", parse_status="succeeded",
                    ),
                    JobGoal(
                        id=ids["goal"], candidate_id=ids["candidate"], offer_target=1,
                        title="后端工程师", filters="", status="active",
                    ),
                ])
                await session.flush()
                session.add(CandidateProfile(
                    id=ids["profile"], resume_id=ids["resume"], full_name="候选人甲",
                    phone="13800000000", email="candidate@example.com", target_job_titles=["后端工程师"],
                    skills=[{"name": "Python"}],
                    work_experience_summary=[{"title": "后端工程师", "company_name": "示例公司", "summary": "服务开发"}],
                    project_experience_summary=[{"name": "支付平台", "summary": "支付系统项目"}],
                    years_of_experience="5年", education="本科",
                ))
                await session.flush()
                session.add(AgentRunContext(
                    id=ids["run"], candidate_id=ids["candidate"], job_goal_id=ids["goal"],
                    resume_id=ids["resume"], candidate_profile_id=ids["profile"],
                    goal_snapshot={"title": "后端工程师"}, status="running", started_at=now, created_at=now,
                ))
                session.add_all([
                    Job(id=ids["job_one"], hr_profile_id=ids["hr_one"], stored_file_object_id=ids["job_file_one"], created_at=now),
                    Job(id=ids["job_two"], hr_profile_id=ids["hr_two"], stored_file_object_id=ids["job_file_two"], created_at=now),
                ])
                await session.flush()
                session.add_all([
                    ParsedJobDescriptionSnapshot(
                        id=ids["snapshot_one"], job_id=ids["job_one"], schema_version="test",
                        fields=_fields("后端工程师"), raw_sections=[],
                    ),
                    ParsedJobDescriptionSnapshot(
                        id=ids["snapshot_two"], job_id=ids["job_two"], schema_version="test",
                        fields=_fields("前端工程师"), raw_sections=[],
                    ),
                    Match(
                        id=ids["match_one"], run_id=ids["run"], candidate_id=ids["candidate"], job_id=ids["job_one"],
                        algorithm_version="test", input_snapshot={}, status="matched",
                        recommendation_reason="test", reason_code="test",
                    ),
                    Match(
                        id=ids["match_two"], run_id=ids["run"], candidate_id=ids["candidate"], job_id=ids["job_two"],
                        algorithm_version="test", input_snapshot={}, status="matched",
                        recommendation_reason="test", reason_code="test",
                    ),
                ])
                await session.commit()

            async with database.session_factory() as session:
                repository = MatchingRepository(session)
                async with repository.transaction():
                    match_one = await session.get(Match, ids["match_one"])
                    match_two = await session.get(Match, ids["match_two"])
                    assert match_one is not None and match_two is not None
                    app_one = await repository.ensure_application(match=match_one)
                    app_two = await repository.ensure_application(match=match_two)
                app_one_id, app_two_id = app_one.id, app_two.id
                ids["app_one"], ids["app_two"] = app_one_id, app_two_id

                async with repository.transaction():
                    repeated = await repository.ensure_application(match=match_one)
                    conversation_one = await session.scalar(
                        select(Conversation).where(Conversation.application_id == app_one_id)
                    )
                    assert repeated.id == app_one_id
                    assert conversation_one is not None
                    assert await session.scalar(
                        select(func.count(Conversation.id)).where(Conversation.application_id == app_one_id)
                    ) == 1
                assert app_two_id != app_one_id

            responder = FakeResponder()
            async with database.session_factory() as session:
                service = ConversationService(repository=ConversationRepository(session), responder=responder)
                listed = await service.list_current_for_hr(hr_profile_id=ids["hr_one"])
                assert len(listed) == 1
                assert listed[0].application_id == app_one_id
                assert listed[0].messages == []
                with pytest.raises(ConversationNotFoundError):
                    await service.get_messages_for_hr(
                        application_id=app_two_id, conversation_id=listed[0].id, hr_profile_id=ids["hr_one"]
                    )
                response = await service.send_message(
                    application_id=app_one_id, conversation_id=listed[0].id, hr_profile_id=ids["hr_one"],
                    client_message_id="fact-1", content="项目经历是什么？",
                )
                assert len(response.new_messages) == 2
                assert response.agent_turn.turn_status == "completed"
                assert responder.facts[0]["skills"] == ["Python"]
                assert "candidate@example.com" not in str(responder.facts[0])
                assert "13800000000" not in str(responder.facts[0])

                duplicate = await service.send_message(
                    application_id=app_one_id, conversation_id=listed[0].id, hr_profile_id=ids["hr_one"],
                    client_message_id="fact-1", content="项目经历是什么？",
                )
                assert duplicate.received_message.id == response.received_message.id
                assert duplicate.agent_turn.id == response.agent_turn.id
                assert len(duplicate.new_messages) == 2

                negative = await service.send_message(
                    application_id=app_one_id, conversation_id=listed[0].id, hr_profile_id=ids["hr_one"],
                    client_message_id="negative-training-1", content="你的工作经历中有包括大模型训练吗？",
                )
                assert negative.new_messages[-1].content == NEGATIVE_TRAINING_REPLY

                fallback = await service.send_message(
                    application_id=app_one_id, conversation_id=listed[0].id, hr_profile_id=ids["hr_one"],
                    client_message_id="unsupported-1", content="出生地是什么？",
                )
                assert fallback.new_messages[-1].content == FALLBACK_REPLY
                failed = await service.send_message(
                    application_id=app_one_id, conversation_id=listed[0].id, hr_profile_id=ids["hr_one"],
                    client_message_id="provider-failure-1", content="provider failure",
                )
                assert failed.new_messages[-1].content == FALLBACK_REPLY

            delayed = FakeResponder(delay=0.1)
            async def send_concurrently() -> list[object]:
                async def one() -> object:
                    async with database.session_factory() as session:
                        return await ConversationService(
                            repository=ConversationRepository(session), responder=delayed
                        ).send_message(
                            application_id=app_one_id, conversation_id=listed[0].id, hr_profile_id=ids["hr_one"],
                            client_message_id="concurrent-1", content="并发问题",
                        )
                return await asyncio.gather(one(), one())

            concurrent_results = await send_concurrently()
            assert len({result.received_message.id for result in concurrent_results}) == 1
            assert len({result.agent_turn.id for result in concurrent_results}) == 1
            assert all(len(result.new_messages) == 2 for result in concurrent_results)
            assert delayed.calls == 1

            async with database.session_factory() as session:
                assert await session.scalar(
                    select(func.count(Message.id)).where(Message.conversation_id == listed[0].id)
                ) == 10
                assert await session.scalar(
                    select(func.count(AgentTurn.id)).where(AgentTurn.conversation_id == listed[0].id)
                ) == 5
        finally:
            async with database.session_factory() as session:
                application_ids = [ids.get("app_one"), ids.get("app_two")]
                if all(isinstance(value, UUID) for value in application_ids):
                    await session.execute(delete(Application).where(Application.id.in_(application_ids)))
                    await session.execute(delete(Conversation).where(Conversation.application_id.in_(application_ids)))
                await session.execute(delete(Match).where(Match.id.in_([ids["match_one"], ids["match_two"]])))
                await session.execute(delete(ParsedJobDescriptionSnapshot).where(
                    ParsedJobDescriptionSnapshot.id.in_([ids["snapshot_one"], ids["snapshot_two"]])
                ))
                await session.execute(delete(Job).where(Job.id.in_([ids["job_one"], ids["job_two"]])))
                await session.execute(delete(AgentRunContext).where(AgentRunContext.id == ids["run"]))
                await session.execute(delete(JobGoal).where(JobGoal.id == ids["goal"]))
                await session.execute(delete(CandidateProfile).where(CandidateProfile.id == ids["profile"]))
                await session.execute(delete(Resume).where(Resume.id == ids["resume"]))
                await session.execute(delete(StoredFileObject).where(StoredFileObject.id.in_([
                    ids["resume_file"], ids["job_file_one"], ids["job_file_two"]
                ])))
                await session.execute(delete(HrProfile).where(HrProfile.id.in_([ids["hr_one"], ids["hr_two"]])))
                await session.execute(delete(Candidate).where(Candidate.id == ids["candidate"]))
                await session.execute(delete(User).where(User.id == ids["hr_user_two"]))
                await session.execute(delete(User).where(User.id == ids["user"]))
                await session.commit()
            await database.close()

    asyncio.run(exercise())
