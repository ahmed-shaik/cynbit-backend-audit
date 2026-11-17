from __future__ import annotations

from collections.abc import Iterator
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from examples.fastapi.app import create_app
from examples.fastapi.schemas import CandidateApplicationRequest, ContactRequest


class FakeRateLimiter:
    def __init__(self, *, blocked_scope: str | None = None) -> None:
        self.blocked_scope = blocked_scope
        self.calls: list[tuple[str, int, int]] = []

    async def hit(
        self,
        request: Request,
        *,
        scope: str,
        limit: int,
        window_seconds: int,
    ) -> int:
        self.calls.append((scope, limit, window_seconds))
        if scope == self.blocked_scope:
            raise HTTPException(
                status_code=429,
                detail="Please wait before trying again",
                headers={"Retry-After": "17"},
            )
        return 1

    async def close(self) -> None:
        return None


class MemorySubmissionService:
    """Test double for the durable idempotent service contract."""

    def __init__(self, *, fail_with: Exception | None = None) -> None:
        self.contacts: dict[UUID, dict[str, object]] = {}
        self.applications: dict[UUID, dict[str, object]] = {}
        self.fail_with = fail_with

    async def accept_contact_once(self, payload: ContactRequest, key: UUID) -> None:
        self._accept(self.contacts, payload.model_dump(mode="json"), key)

    async def accept_application_once(
        self,
        payload: CandidateApplicationRequest,
        key: UUID,
    ) -> None:
        self._accept(self.applications, payload.model_dump(mode="json"), key)

    def _accept(
        self,
        records: dict[UUID, dict[str, object]],
        payload: dict[str, object],
        key: UUID,
    ) -> None:
        if self.fail_with is not None:
            raise self.fail_with
        previous = records.get(key)
        if previous is not None:
            if previous != payload:
                raise HTTPException(status_code=409, detail="Idempotency key conflict")
            return
        records[key] = payload


@pytest.fixture
def api() -> Iterator[tuple[TestClient, FakeRateLimiter, MemorySubmissionService]]:
    limiter = FakeRateLimiter()
    service = MemorySubmissionService()
    application = create_app(rate_limiter=limiter, submission_service=service)
    with TestClient(application, backend="trio", raise_server_exceptions=False) as client:
        yield client, limiter, service


def test_contact_request_replay_uses_idempotency_service_contract(
    api: tuple[TestClient, FakeRateLimiter, MemorySubmissionService],
) -> None:
    client, limiter, service = api
    key = str(uuid4())
    body = {
        "full_name": "Applicant Name",
        "email": "applicant@example.com",
        "message": "Please contact me about your services.",
    }

    first = client.post("/v1/contact-inquiries", json=body, headers={"Idempotency-Key": key})
    replay = client.post("/v1/contact-inquiries", json=body, headers={"Idempotency-Key": key})

    assert first.status_code == replay.status_code == 202
    assert len(service.contacts) == 1
    assert limiter.calls == [("contact", 5, 60), ("contact", 5, 60)]


def test_same_idempotency_key_with_changed_body_is_rejected(
    api: tuple[TestClient, FakeRateLimiter, MemorySubmissionService],
) -> None:
    client, _, service = api
    key = str(uuid4())
    body = {
        "full_name": "Applicant Name",
        "email": "applicant@example.com",
        "message": "Please contact me about your services.",
    }
    first = client.post("/v1/contact-inquiries", json=body, headers={"Idempotency-Key": key})
    changed = {**body, "message": "A different request with the same key."}
    second = client.post("/v1/contact-inquiries", json=changed, headers={"Idempotency-Key": key})

    assert first.status_code == 202
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "request_failed"
    assert len(service.contacts) == 1


def test_validation_error_does_not_echo_personal_input(
    api: tuple[TestClient, FakeRateLimiter, MemorySubmissionService],
) -> None:
    client, _, _ = api
    response = client.post(
        "/v1/contact-inquiries",
        json={"full_name": "x", "email": "private.person@example.com", "message": "short"},
        headers={"Idempotency-Key": str(uuid4())},
    )

    assert response.status_code == 422
    assert "private.person@example.com" not in response.text
    assert response.json()["error"]["code"] == "invalid_request"


def test_idempotency_header_requires_uuid_v4(
    api: tuple[TestClient, FakeRateLimiter, MemorySubmissionService],
) -> None:
    client, _, _ = api
    response = client.post(
        "/v1/contact-inquiries",
        json={
            "full_name": "Applicant Name",
            "email": "applicant@example.com",
            "message": "Please contact me about your services.",
        },
        headers={"Idempotency-Key": "00000000-0000-1000-8000-000000000001"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_rate_limit_response_is_generic_and_preserves_retry_after() -> None:
    limiter = FakeRateLimiter(blocked_scope="contact")
    service = MemorySubmissionService()
    application = create_app(rate_limiter=limiter, submission_service=service)
    with TestClient(application, backend="trio", raise_server_exceptions=False) as client:
        response = client.post(
            "/v1/contact-inquiries",
            json={
                "full_name": "Applicant Name",
                "email": "applicant@example.com",
                "message": "Please contact me about your services.",
            },
            headers={"Idempotency-Key": str(uuid4())},
        )

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "17"
    assert response.json()["error"]["code"] == "rate_limited"
    assert "applicant@example.com" not in response.text


def test_unexpected_service_error_is_not_returned_to_client(
    api: tuple[TestClient, FakeRateLimiter, MemorySubmissionService],
) -> None:
    client, _, service = api
    service.fail_with = RuntimeError("private.person@example.com internal detail")
    response = client.post(
        "/v1/contact-inquiries",
        json={
            "full_name": "Applicant Name",
            "email": "applicant@example.com",
            "message": "Please contact me about your services.",
        },
        headers={"Idempotency-Key": str(uuid4())},
    )

    assert response.status_code == 500
    assert "private.person@example.com" not in response.text
    assert response.json()["error"]["code"] == "internal_error"


def test_candidate_application_create_is_public_but_scoped_to_submission_contract(
    api: tuple[TestClient, FakeRateLimiter, MemorySubmissionService],
) -> None:
    client, limiter, service = api
    response = client.post(
        "/v1/candidate-applications",
        json={
            "job_id": "backend-intern",
            "full_name": "Applicant Name",
            "email": "applicant@example.com",
            "skills": ["Python", "PostgreSQL"],
            "statement": "I would like to apply for this backend role.",
        },
        headers={"Idempotency-Key": str(uuid4())},
    )

    assert response.status_code == 202
    assert len(service.applications) == 1
    assert limiter.calls == [("candidate-application", 3, 60)]
