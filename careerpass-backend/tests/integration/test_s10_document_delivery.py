"""PostgreSQL and local-object-storage verification for S10-02."""

import asyncio
import hashlib
import os
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from app.infrastructure.database import create_database
from app.infrastructure.database.models import (
    AgentRunContext,
    Candidate,
    CandidateDocument,
    CandidateProfile,
    Conversation,
    HrProfile,
    Job,
    JobGoal,
    Match,
    MessageAttachment,
    ParsedJobDescriptionSnapshot,
    Resume,
    StoredFileObject,
    User,
)
from app.infrastructure.storage.local import LocalObjectStorage
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.matching_repository import MatchingRepository
from app.repositories.object_storage_repository import ObjectStorageRepository
from app.schemas.communication import ResumeAnswerDraft
from app.schemas.job_description import ParsedJobDescriptionFields
from app.services.conversation_service import AttachmentExpiredError, ConversationService

pytestmark = pytest.mark.integration


class NotCalledResponder:
    async def answer(self, *, question: str, facts: dict[str, object]) -> ResumeAnswerDraft:
        raise AssertionError("S10-02 must not call the Qwen responder")


def _database_url() -> str:
    if os.getenv("RUN_INTEGRATION_TESTS") != "true":
        pytest.skip("set RUN_INTEGRATION_TESTS=true after starting the integration compose stack")
    value = os.getenv("TEST_DATABASE_URL")
    if not value:
        pytest.skip("TEST_DATABASE_URL is required for integration tests")
    return value


def _fields() -> dict[str, object]:
    def text_field(value: str, order: int) -> dict[str, object]:
        return {
            "raw": value,
            "normalized": value,
            "source_heading": "测试",
            "source_order": order,
        }

    return ParsedJobDescriptionFields(
        title=text_field("后端工程师", 0),
        company_name=text_field("示例公司", 1),
        location=text_field("上海", 2),
        salary_range={"raw": "20K", "min": 20000, "max": 20000, "currency": "CNY", "period": "month", "source_heading": "测试", "source_order": 3},
        responsibilities={"raw": "开发", "items": [], "source_heading": "职责", "source_order": 4},
        requirements={"raw": "经验", "items": [], "source_heading": "要求", "source_order": 5},
    ).model_dump(mode="json")


def test_s10_02_postgresql_attachment_delivery_and_retention() -> None:
    database_url = _database_url()
    ids = {name: uuid4() for name in (
        "user", "candidate", "hr", "goal", "run", "profile", "resume", "resume_file",
        "job", "job_file", "snapshot", "match", "document", "document_file",
    )}
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "candidate_preparation"
        / "candidate_documents"
        / "学籍验证报告.pdf"
    )
    content = fixture_path.read_bytes() + f"\nfixture-run-{ids['document_file']}".encode()
    storage_root = Path(".s10-02-integration-objects") / str(uuid4())
    storage_root.mkdir(parents=True, exist_ok=True)
    storage = LocalObjectStorage(str(storage_root))
    upload = storage.put(content)
    now = datetime.now(UTC)

    async def exercise() -> None:
        database = create_database(database_url)
        try:
            async with database.session_factory() as session:
                session.add_all([
                    User(id=ids["user"], username=f"s10-02-{ids['user']}", password_hash="test"),
                    Candidate(id=ids["candidate"], user_id=ids["user"], name="候选人甲"),
                    HrProfile(id=ids["hr"], user_id=ids["user"], name="HR 甲"),
                    StoredFileObject(
                        id=ids["resume_file"], storage_key=f"resume-{ids['resume_file']}",
                        content_sha256=str(ids["resume_file"]), detected_mime_type="application/pdf",
                        file_size_bytes=1, status="ready",
                    ),
                    StoredFileObject(
                        id=ids["job_file"], storage_key=f"job-{ids['job_file']}",
                        content_sha256=str(ids["job_file"]), detected_mime_type="text/markdown",
                        file_size_bytes=1, status="ready",
                    ),
                    StoredFileObject(
                        id=ids["document_file"], storage_key=upload.storage_key,
                        content_sha256=hashlib.sha256(content).hexdigest(),
                        detected_mime_type="application/pdf", file_size_bytes=len(content), status="ready",
                    ),
                ])
                await session.flush()
                session.add_all([
                    JobGoal(
                        id=ids["goal"], candidate_id=ids["candidate"], offer_target=1,
                        title="后端工程师", filters="", status="active",
                    ),
                    Resume(
                        id=ids["resume"], candidate_id=ids["candidate"], file_name="resume.pdf",
                        stored_file_object_id=ids["resume_file"], file_type="pdf", parse_status="succeeded",
                    ),
                    CandidateDocument(
                        id=ids["document"], candidate_id=ids["candidate"], document_type="certificate",
                        document_name="学籍验证报告.pdf", file_type="pdf",
                        stored_file_object_id=ids["document_file"],
                    ),
                ])
                await session.flush()
                session.add(
                    CandidateProfile(
                        id=ids["profile"], resume_id=ids["resume"], full_name="候选人甲",
                        phone="13800000000", email="candidate@example.com", target_job_titles=["后端工程师"],
                        skills=[{"name": "Python"}], work_experience_summary=[], project_experience_summary=[],
                        years_of_experience="5年", education="本科",
                    )
                )
                await session.flush()
                session.add(AgentRunContext(
                    id=ids["run"], candidate_id=ids["candidate"], job_goal_id=ids["goal"],
                    resume_id=ids["resume"], candidate_profile_id=ids["profile"],
                    goal_snapshot={"title": "后端工程师"}, status="running", started_at=now, created_at=now,
                ))
                session.add(Job(
                    id=ids["job"], hr_profile_id=ids["hr"], stored_file_object_id=ids["job_file"], created_at=now,
                ))
                await session.flush()
                session.add(ParsedJobDescriptionSnapshot(
                    id=ids["snapshot"], job_id=ids["job"], schema_version="test",
                    fields=_fields(), raw_sections=[],
                ))
                session.add(Match(
                    id=ids["match"], run_id=ids["run"], candidate_id=ids["candidate"], job_id=ids["job"],
                    algorithm_version="test", input_snapshot={}, status="matched",
                    recommendation_reason="test", reason_code="test",
                ))
                await session.commit()

            async with database.session_factory() as session:
                matching = MatchingRepository(session)
                async with matching.transaction():
                    match = await session.get(Match, ids["match"])
                    assert match is not None
                    application = await matching.ensure_application(match=match)
                application_id = application.id
                conversation = await session.scalar(
                    select(Conversation).where(Conversation.application_id == application_id)
                )
                assert conversation is not None
                conversation_id = conversation.id

            async with database.session_factory() as session:
                service = ConversationService(
                    repository=ConversationRepository(session),
                    responder=NotCalledResponder(),
                    storage=storage,
                )
                result = await service.send_message(
                    application_id=application_id, conversation_id=conversation_id, hr_profile_id=ids["hr"],
                    client_message_id="student-status-1", content="请把你的学籍验证报告发一下。",
                )
                attachment = result.new_messages[-1].attachments[0]
                assert result.agent_turn.scene == "document_delivery"
                assert result.agent_turn.outcome == "attachment_sent"
                assert len(result.new_messages) == 2
                assert len(result.new_messages[-1].attachments) == 1
                assert attachment.file_name == "学籍验证报告.pdf"
                assert attachment.file_size_bytes == len(content)

                duplicate = await service.send_message(
                    application_id=application_id, conversation_id=conversation_id, hr_profile_id=ids["hr"],
                    client_message_id="student-status-1", content="请把你的学籍验证报告发一下。",
                )
                assert duplicate.received_message.id == result.received_message.id
                assert duplicate.new_messages[-1].id == result.new_messages[-1].id

                downloaded = await service.download_attachment(
                    application_id=application_id, message_id=result.new_messages[-1].id,
                    attachment_id=attachment.id, hr_profile_id=ids["hr"],
                )
                assert downloaded.content == content
                assert downloaded.file_name == "学籍验证报告.pdf"

                await session.execute(delete(CandidateDocument).where(CandidateDocument.id == ids["document"]))
                await session.commit()
                downloaded_after_delete = await service.download_attachment(
                    application_id=application_id, message_id=result.new_messages[-1].id,
                    attachment_id=attachment.id, hr_profile_id=ids["hr"],
                )
                assert downloaded_after_delete.content == content

                attachment_row = await session.get(MessageAttachment, attachment.id)
                attachment_row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
                await session.commit()
                with pytest.raises(AttachmentExpiredError):
                    await service.download_attachment(
                        application_id=application_id, message_id=result.new_messages[-1].id,
                        attachment_id=attachment.id, hr_profile_id=ids["hr"],
                    )

                claims = await ObjectStorageRepository(session).claim_expired_unreferenced(
                    older_than=datetime.now(UTC) + timedelta(hours=1), limit=10
                )
                assert any(claim.object_id == ids["document_file"] for claim in claims)
                for claim in claims:
                    await ObjectStorageRepository(session).restore_after_delete_failure(claim)

            async with database.session_factory() as session:
                await session.execute(delete(AgentRunContext).where(AgentRunContext.id == ids["run"]))
                await session.execute(delete(Match).where(Match.id == ids["match"]))
                await session.execute(delete(ParsedJobDescriptionSnapshot).where(ParsedJobDescriptionSnapshot.id == ids["snapshot"]))
                await session.execute(delete(Job).where(Job.id == ids["job"]))
                await session.execute(delete(JobGoal).where(JobGoal.id == ids["goal"]))
                await session.execute(delete(CandidateDocument).where(CandidateDocument.id == ids["document"]))
                await session.execute(delete(CandidateProfile).where(CandidateProfile.id == ids["profile"]))
                await session.execute(delete(Resume).where(Resume.id == ids["resume"]))
                await session.execute(delete(StoredFileObject).where(StoredFileObject.id.in_([
                    ids["resume_file"], ids["job_file"], ids["document_file"],
                ])))
                await session.execute(delete(HrProfile).where(HrProfile.id == ids["hr"]))
                await session.execute(delete(Candidate).where(Candidate.id == ids["candidate"]))
                await session.execute(delete(User).where(User.id == ids["user"]))
                await session.commit()
        finally:
            await database.close()
            shutil.rmtree(storage_root, ignore_errors=True)

    asyncio.run(exercise())
