"""Tests for FastAPI application-factory and exception behavior."""

from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.testclient import TestClient

from app.api.dependencies.auth import get_current_identity
from app.api.dependencies.services import get_login_service, get_registration_service
from app.core.errors import ErrorCode
from app.core.exceptions import AppException
from app.core.identity import CurrentIdentity
from app.main import create_app
from app.schemas.auth import AuthenticationResponse
from app.services.login_service import InvalidCredentialsError
from app.services.registration_service import UsernameAlreadyExistsError


class StaticRuntimeHealthService:
    """Test double that avoids real external dependency connections."""

    def __init__(self, ready: bool) -> None:
        self._ready = ready

    async def is_ready(self) -> bool:
        return self._ready


def test_root_returns_success_envelope(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "code": 200,
        "msg": "success",
        "data": {"service": "CareerPass API"},
    }
    assert response.headers["content-type"] == "application/json; charset=utf-8"
    assert response.headers["X-Request-ID"]


def test_request_id_is_preserved_and_query_is_not_logged(client: TestClient, caplog) -> None:
    response = client.get(
        "/?token=never-log-this",
        headers={"X-Request-ID": "gateway.request-7"},
    )

    assert response.headers["X-Request-ID"] == "gateway.request-7"
    careerpass_records = [
        record for record in caplog.records if record.name.startswith("careerpass.")
    ]
    assert careerpass_records
    assert all("never-log-this" not in record.getMessage() for record in careerpass_records)
    assert any(
        record.name == "careerpass.request"
        and getattr(record, "path", None) == "/"
        and not hasattr(record, "query")
        for record in careerpass_records
    )


def test_liveness_does_not_depend_on_external_services(client: TestClient) -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {
        "code": 200,
        "msg": "success",
        "data": {"status": "alive"},
    }


def test_auth_me_returns_the_trusted_identity_in_the_uniform_envelope() -> None:
    app = create_app()

    async def identity_override() -> CurrentIdentity:
        return CurrentIdentity(
            user_id=UUID("a2c51d36-f30d-4878-b38c-7951a97d1c2a"),
            username="alice",
            name="Alice",
            roles=("candidate",),
            active_role="candidate",
            candidate_id=UUID("3911cbf8-7a30-4e3c-8e18-4afc4c3260bf"),
        )

    app.dependency_overrides[get_current_identity] = identity_override
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json() == {
        "code": 200,
        "msg": "success",
        "data": {
            "user_id": "a2c51d36-f30d-4878-b38c-7951a97d1c2a",
            "username": "alice",
            "name": "Alice",
            "roles": ["candidate"],
            "active_role": "candidate",
            "candidate_id": "3911cbf8-7a30-4e3c-8e18-4afc4c3260bf",
            "hr_profile_id": None,
            "profile_status": None,
        },
    }


def test_auth_me_rejects_a_missing_bearer_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json() == {
        "code": 401,
        "msg": "authentication failed",
        "data": None,
    }


def test_register_and_login_routes_use_the_uniform_response_contract() -> None:
    app = create_app()
    authentication_response = AuthenticationResponse(
        access_token="token-for-client",
        expires_in=1800,
        user={
            "user_id": UUID("a2c51d36-f30d-4878-b38c-7951a97d1c2a"),
            "roles": ["candidate"],
            "active_role": "candidate",
            "candidate_id": UUID("3911cbf8-7a30-4e3c-8e18-4afc4c3260bf"),
            "profile_status": "incomplete",
        },
    )

    class RegistrationServiceDouble:
        async def register(self, _: object) -> AuthenticationResponse:
            return authentication_response

    class LoginServiceDouble:
        async def login(self, _: object) -> AuthenticationResponse:
            return authentication_response

    async def registration_override() -> RegistrationServiceDouble:
        return RegistrationServiceDouble()

    async def login_override() -> LoginServiceDouble:
        return LoginServiceDouble()

    app.dependency_overrides[get_registration_service] = registration_override
    app.dependency_overrides[get_login_service] = login_override
    request_body = {"username": "alice", "password": "weak", "name": "Alice"}
    with TestClient(app, raise_server_exceptions=False) as client:
        register_response = client.post("/api/v1/auth/register", json=request_body)
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "alice", "password": "weak"},
        )

    expected_data = authentication_response.model_dump(mode="json")
    assert register_response.status_code == 200
    assert register_response.json() == {"code": 200, "msg": "success", "data": expected_data}
    assert login_response.status_code == 200
    assert login_response.json() == {"code": 200, "msg": "success", "data": expected_data}


def test_auth_routes_map_domain_failures_without_leaking_details() -> None:
    app = create_app()

    class RegistrationServiceDouble:
        async def register(self, _: object) -> AuthenticationResponse:
            raise UsernameAlreadyExistsError

    class LoginServiceDouble:
        async def login(self, _: object) -> AuthenticationResponse:
            raise InvalidCredentialsError

    async def registration_override() -> RegistrationServiceDouble:
        return RegistrationServiceDouble()

    async def login_override() -> LoginServiceDouble:
        return LoginServiceDouble()

    app.dependency_overrides[get_registration_service] = registration_override
    app.dependency_overrides[get_login_service] = login_override
    with TestClient(app, raise_server_exceptions=False) as client:
        duplicate = client.post(
            "/api/v1/auth/register",
            json={"username": "alice", "password": "StrongPassword123!"},
        )
        invalid_credentials = client.post(
            "/api/v1/auth/login",
            json={"username": "alice", "password": "StrongPassword123!"},
        )

    assert duplicate.status_code == 409
    assert duplicate.json() == {
        "code": 409,
        "msg": "username already exists",
        "data": None,
    }
    assert invalid_credentials.status_code == 401
    assert invalid_credentials.json() == {
        "code": 401,
        "msg": "invalid credentials",
        "data": None,
    }


def test_auth_routes_map_invalid_request_data_to_the_uniform_validation_error(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "ab", "password": "weak"},
    )

    assert response.status_code == 400
    assert response.json() == {
        "code": 400,
        "msg": "validation error",
        "data": None,
    }


def test_readiness_returns_safe_success_and_failure_contracts() -> None:
    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        app.state.runtime_health_service = StaticRuntimeHealthService(ready=True)
        ready_response = client.get("/health/ready")
        app.state.runtime_health_service = StaticRuntimeHealthService(ready=False)
        unavailable_response = client.get("/health/ready")

    assert ready_response.status_code == 200
    assert ready_response.json() == {
        "code": 200,
        "msg": "success",
        "data": {"status": "ready"},
    }
    assert unavailable_response.status_code == 503
    assert unavailable_response.json() == {
        "code": 500,
        "msg": "service not ready",
        "data": None,
    }
    assert "localhost" not in unavailable_response.text


def test_unknown_route_returns_not_found_envelope(client: TestClient) -> None:
    response = client.get("/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {
        "code": 404,
        "msg": "not found",
        "data": None,
    }
    assert response.headers["X-Request-ID"]


def test_known_http_exception_maps_to_safe_request_failed_envelope() -> None:
    app = create_app()
    router = APIRouter()

    @router.get("/unauthorized")
    async def raise_unauthorized() -> None:
        raise HTTPException(status_code=401, detail="do not return detail")

    app.include_router(router)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/unauthorized")

    assert response.status_code == 401
    assert response.json() == {
        "code": 401,
        "msg": "request failed",
        "data": None,
    }


def test_validation_error_uses_safe_uniform_envelope() -> None:
    app = create_app()
    router = APIRouter()

    @router.get("/validation")
    async def validate_value(value: int) -> dict[str, int]:
        return {"value": value}

    app.include_router(router)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/validation?value=not-an-int")

    assert response.status_code == 400
    assert response.json() == {
        "code": 400,
        "msg": "validation error",
        "data": None,
    }


def test_known_application_exception_uses_safe_envelope() -> None:
    app = create_app()
    router = APIRouter()

    @router.get("/conflict")
    async def raise_conflict() -> None:
        raise AppException(
            status_code=409,
            code=ErrorCode.CONFLICT,
            message="business conflict",
        )

    app.include_router(router)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/conflict")

    assert response.status_code == 409
    assert response.json() == {
        "code": 409,
        "msg": "business conflict",
        "data": None,
    }
    assert response.headers["X-Request-ID"]


def test_unexpected_exception_does_not_leak_details(caplog) -> None:
    app = create_app()
    router = APIRouter()

    @router.get("/unexpected")
    async def raise_unexpected() -> None:
        raise RuntimeError("database-password=not-for-client")

    app.include_router(router)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/unexpected")

    assert response.status_code == 500
    assert response.json() == {
        "code": 500,
        "msg": "internal server error",
        "data": None,
    }
    assert "database-password=not-for-client" not in caplog.text
    assert response.headers["X-Request-ID"]
