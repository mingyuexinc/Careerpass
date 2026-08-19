"""PostgreSQL verification for the S-09 authorization and transaction boundary."""

import asyncio
import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from app.core.identity import CurrentIdentity
from app.infrastructure.database import create_database
from app.infrastructure.database.models import (
    AgentRunContext,
    Application,
    Candidate,
    CandidateProfile,
    HrProfile,
    Job,
    JobGoal,
    Match,
    ParsedJobDescriptionSnapshot,
    ProgressEvent,
    Resume,
    StoredFileObject,
    User,
    UserRole,
)
from app.repositories.application_repository import ApplicationRepository
from app.repositories.debug_reset_repository import DebugResetRepository
from app.repositories.job_repository import JobRepository
from app.repositories.matching_repository import MatchingRepository
from app.schemas.job_description import ParsedJobDescriptionFields
from app.services.application_service import ApplicationService
from app.services.job_service import JobService
from app.services.matching_service import MatchingService

pytestmark = pytest.mark.integration


def _fields(title: str, company: str) -> dict[str, object]:
    def text_field(raw: str, order: int) -> dict[str, object]:
        return {
            "raw": raw,
            "normalized": raw,
            "source_heading": "测试",
            "source_order": order,
        }

    return ParsedJobDescriptionFields(
        title=text_field(title, 0),
        company_name=text_field(company, 1),
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


def _require_integration_database() -> str:
    if os.getenv("RUN_INTEGRATION_TESTS") != "true":
        pytest.skip("set RUN_INTEGRATION_TESTS=true after starting the integration compose stack")
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is required for integration tests")
    return database_url


def test_hr_application_query_update_and_offer_linkage_use_postgresql() -> None:
    database_url = _require_integration_database()
    ids = {"user": uuid4(), "candidate": uuid4(), "hr": uuid4(), "goal": uuid4(), "run": uuid4()}
    ids.update({key: uuid4() for key in ("profile", "resume", "resume_file", "job_file_1", "job_file_2")})
    ids.update({key: uuid4() for key in ("job_1", "job_2", "snapshot_1", "snapshot_2", "match_1", "match_2", "app_1", "app_2")})
    now = datetime.now(UTC)

    async def exercise() -> None:
        database = create_database(database_url)
        try:
            async with database.session_factory() as session:
                session.add_all(
                    [
                        User(id=ids["user"], username=f"s09-{ids['user']}", password_hash="test"),
                        Candidate(id=ids["candidate"], user_id=ids["user"], name="Alex Chen"),
                        HrProfile(id=ids["hr"], user_id=ids["user"], name="Mia Wang"),
                        UserRole(id=uuid4(), user_id=ids["user"], role="hr"),
                    ]
                )
                await session.flush()
                session.add_all(
                    [
                        StoredFileObject(
                            id=ids["resume_file"],
                            storage_key=f"s09-resume-{ids['resume_file']}",
                            content_sha256=str(ids["resume_file"]),
                            detected_mime_type="application/pdf",
                            file_size_bytes=1,
                            status="ready",
                        ),
                        StoredFileObject(
                            id=ids["job_file_1"],
                            storage_key=f"s09-job-1-{ids['job_file_1']}",
                            content_sha256=str(ids["job_file_1"]),
                            detected_mime_type="text/markdown",
                            file_size_bytes=1,
                            status="ready",
                        ),
                        StoredFileObject(
                            id=ids["job_file_2"],
                            storage_key=f"s09-job-2-{ids['job_file_2']}",
                            content_sha256=str(ids["job_file_2"]),
                            detected_mime_type="text/markdown",
                            file_size_bytes=1,
                            status="ready",
                        ),
                    ]
                )
                await session.flush()
                session.add_all(
                    [
                        Resume(
                            id=ids["resume"],
                            candidate_id=ids["candidate"],
                            file_name="resume.pdf",
                            stored_file_object_id=ids["resume_file"],
                            file_type="pdf",
                            parse_status="succeeded",
                        ),
                    ]
                )
                await session.flush()
                session.add_all(
                    [
                        CandidateProfile(
                            id=ids["profile"],
                            resume_id=ids["resume"],
                            full_name="Alex Chen",
                            target_job_titles=["工程师"],
                            years_of_experience="5年",
                        ),
                        JobGoal(
                            id=ids["goal"],
                            candidate_id=ids["candidate"],
                            offer_target=1,
                            title="工程师",
                            filters="",
                            status="active",
                        ),
                    ]
                )
                await session.flush()
                session.add_all(
                    [
                        AgentRunContext(
                            id=ids["run"],
                            candidate_id=ids["candidate"],
                            job_goal_id=ids["goal"],
                            resume_id=ids["resume"],
                            candidate_profile_id=ids["profile"],
                            goal_snapshot={"title": "工程师"},
                            status="running",
                            started_at=now,
                            created_at=now,
                        ),
                    ]
                )
                await session.flush()
                session.add_all(
                    [
                        Job(
                            id=ids["job_1"],
                            hr_profile_id=ids["hr"],
                            stored_file_object_id=ids["job_file_1"],
                            created_at=now,
                        ),
                        Job(
                            id=ids["job_2"],
                            hr_profile_id=ids["hr"],
                            stored_file_object_id=ids["job_file_2"],
                            created_at=now,
                        ),
                    ]
                )
                await session.flush()
                session.add_all(
                    [
                        ParsedJobDescriptionSnapshot(
                            id=ids["snapshot_1"],
                            job_id=ids["job_1"],
                            schema_version="test",
                            fields=_fields("后端工程师", "示例公司"),
                            raw_sections=[],
                        ),
                        ParsedJobDescriptionSnapshot(
                            id=ids["snapshot_2"],
                            job_id=ids["job_2"],
                            schema_version="test",
                            fields=_fields("前端工程师", "示例公司"),
                            raw_sections=[],
                        ),
                    ]
                )
                await session.flush()
                session.add_all(
                    [
                        Match(
                            id=ids["match_1"],
                            run_id=ids["run"],
                            candidate_id=ids["candidate"],
                            job_id=ids["job_1"],
                            algorithm_version="test",
                            input_snapshot={},
                            status="application_created",
                            recommendation_reason="test",
                            reason_code="test",
                        ),
                        Match(
                            id=ids["match_2"],
                            run_id=ids["run"],
                            candidate_id=ids["candidate"],
                            job_id=ids["job_2"],
                            algorithm_version="test",
                            input_snapshot={},
                            status="application_created",
                            recommendation_reason="test",
                            reason_code="test",
                        ),
                    ]
                )
                await session.flush()
                session.add_all(
                    [
                        Application(
                            id=ids["app_1"],
                            run_id=ids["run"],
                            match_id=ids["match_1"],
                            candidate_id=ids["candidate"],
                            job_id=ids["job_1"],
                            status="submitted",
                            applied_at=now,
                            created_at=now,
                            updated_at=now,
                        ),
                        Application(
                            id=ids["app_2"],
                            run_id=ids["run"],
                            match_id=ids["match_2"],
                            candidate_id=ids["candidate"],
                            job_id=ids["job_2"],
                            status="submitted",
                            applied_at=now,
                            created_at=now,
                            updated_at=now,
                        ),
                    ]
                )
                await session.flush()
                session.add_all(
                    [
                        ProgressEvent(
                            id=uuid4(),
                            application_id=ids["app_1"],
                            candidate_id=ids["candidate"],
                            job_id=ids["job_1"],
                            event_type="application_created",
                            to_status="submitted",
                            actor="agent",
                            created_at=now,
                        ),
                        ProgressEvent(
                            id=uuid4(),
                            application_id=ids["app_2"],
                            candidate_id=ids["candidate"],
                            job_id=ids["job_2"],
                            event_type="application_created",
                            to_status="submitted",
                            actor="agent",
                            created_at=now,
                        ),
                    ]
                )
                await session.commit()

            async with database.session_factory() as session:
                service = ApplicationService(repository=ApplicationRepository(session))
                listed = await service.list_current_for_hr(hr_profile_id=ids["hr"])
                assert len(listed) == 2
                assert {item.candidate_name for item in listed} == {"Alex Chen"}
                assert {item.job_title for item in listed} == {"后端工程师", "前端工程师"}

                updated = await service.update_status(
                    application_id=ids["app_1"],
                    hr_profile_id=ids["hr"],
                    status="offer",
                )
                assert updated.status == "offer"
                other = await service.update_status(
                    application_id=ids["app_2"],
                    hr_profile_id=ids["hr"],
                    status="screening",
                )
                assert other.status == "screening"
                terminated = await service.update_status(
                    application_id=ids["app_2"],
                    hr_profile_id=ids["hr"],
                    status="terminated",
                )
                assert terminated.status == "terminated"
                candidate_view = await MatchingService(
                    repository=MatchingRepository(session)
                ).list_current_applications(candidate_id=ids["candidate"])
                assert {item.status for item in candidate_view.applications} == {
                    "offer",
                    "terminated",
                }
                events = (
                    await session.execute(
                        select(ProgressEvent).where(ProgressEvent.application_id == ids["app_1"])
                    )
                ).scalars().all()
                assert any(
                    event.event_type == "application_status_updated"
                    and event.from_status == "submitted"
                    and event.to_status == "offer"
                    and event.actor == "hr"
                    for event in events
                )
                hr_jobs = await JobService(repository=JobRepository(session)).list_current_for_hr(
                    hr_profile_id=ids["hr"]
                )
                assert len(hr_jobs) == 2
                assert {item.job_title for item in hr_jobs} == {
                    "后端工程师",
                    "前端工程师",
                }
                await session.commit()

                reset_repository = DebugResetRepository(session)
                async with reset_repository.transaction():
                    await reset_repository.reset_current_account(
                        CurrentIdentity(
                            user_id=ids["user"],
                            username="s09-hr",
                            name="Mia Wang",
                            roles=("hr",),
                            active_role="hr",
                            hr_profile_id=ids["hr"],
                        )
                    )

                assert (
                    await session.scalar(
                        select(Application).where(Application.id == ids["app_1"])
                    )
                    is None
                )
                assert (
                    await session.scalar(select(Job).where(Job.id == ids["job_1"])) is None
                )

            async with database.session_factory() as session:
                run = await session.get(AgentRunContext, ids["run"])
                goal = await session.get(JobGoal, ids["goal"])
                second = await session.get(Application, ids["app_2"])
                assert run is not None and run.status == "finished"
                assert run.finish_reason == "offer_target_reached"
                assert goal is not None and goal.status == "achieved"
                assert second is None
                assert (
                    await session.scalar(
                        select(ProgressEvent).where(
                            ProgressEvent.application_id == ids["app_1"]
                        )
                    )
                    is None
                )
        finally:
            async with database.session_factory() as session:
                await session.execute(
                    delete(ProgressEvent).where(
                        ProgressEvent.application_id.in_([ids["app_1"], ids["app_2"]])
                    )
                )
                await session.execute(
                    delete(Application).where(
                        Application.id.in_([ids["app_1"], ids["app_2"]])
                    )
                )
                await session.execute(
                    delete(Match).where(Match.id.in_([ids["match_1"], ids["match_2"]]))
                )
                await session.execute(
                    delete(ParsedJobDescriptionSnapshot).where(
                        ParsedJobDescriptionSnapshot.id.in_([ids["snapshot_1"], ids["snapshot_2"]])
                    )
                )
                await session.execute(
                    delete(Job).where(Job.id.in_([ids["job_1"], ids["job_2"]]))
                )
                await session.execute(delete(AgentRunContext).where(AgentRunContext.id == ids["run"]))
                await session.execute(delete(JobGoal).where(JobGoal.id == ids["goal"]))
                await session.execute(delete(CandidateProfile).where(CandidateProfile.id == ids["profile"]))
                await session.execute(delete(Resume).where(Resume.id == ids["resume"]))
                await session.execute(
                    delete(StoredFileObject).where(
                        StoredFileObject.id.in_([ids["resume_file"], ids["job_file_1"], ids["job_file_2"]])
                    )
                )
                await session.execute(delete(UserRole).where(UserRole.user_id == ids["user"]))
                await session.execute(delete(HrProfile).where(HrProfile.id == ids["hr"]))
                await session.execute(delete(Candidate).where(Candidate.id == ids["candidate"]))
                await session.execute(delete(User).where(User.id == ids["user"]))
                await session.commit()
            await database.close()

    asyncio.run(exercise())
