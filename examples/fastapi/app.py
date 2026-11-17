"""Illustrative FastAPI boundary; persistence and email adapters are injected."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Annotated, Protocol
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import UUID4
from redis.asyncio import Redis
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from examples.fastapi.schemas import CandidateApplicationRequest, ContactRequest
from examples.fastapi.security import PublicRateLimiter, RateLimiterPort, rate_limit

logger = logging.getLogger("assessment_api")
IdempotencyKey = Annotated[UUID4, Header(alias="Idempotency-Key")]


class SubmissionService(Protocol):
    """Implement with a DB transaction, unique idempotency constraint, and outbox."""

    async def accept_contact_once(self, payload: ContactRequest, key: UUID) -> None: ...

    async def accept_application_once(
        self,
        payload: CandidateApplicationRequest,
        key: UUID,
    ) -> None: ...


def get_submission_service(request: Request) -> SubmissionService:
    service: SubmissionService | None = getattr(request.app.state, "submission_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="Submission is temporarily unavailable")
    return service


def create_app(
    *,
    rate_limiter: RateLimiterPort | None = None,
    submission_service: SubmissionService | None = None,
) -> FastAPI:
    """Create an app with injected adapters for deployment or isolated tests."""

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        managed_limiter = rate_limiter
        owns_limiter = managed_limiter is None
        if managed_limiter is None:
            redis_url = os.environ["REDIS_URL"]
            fingerprint_key = os.environ["RATE_LIMIT_HMAC_KEY"].encode("utf-8")
            redis = Redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1,
                health_check_interval=30,
            )
            managed_limiter = PublicRateLimiter(redis, fingerprint_key)

        application.state.rate_limiter = managed_limiter
        if submission_service is not None:
            application.state.submission_service = submission_service
        try:
            yield
        finally:
            if owns_limiter:
                await managed_limiter.close()

    application = FastAPI(title="Recruitment API example", lifespan=lifespan)

    # Leave BROWSER_CORS_ORIGINS empty for same-origin or server-to-server calls.
    # If browser cross-origin calls are required, set exact origins in deployment.
    browser_origins = [
        origin.strip()
        for origin in os.environ.get("BROWSER_CORS_ORIGINS", "").split(",")
        if origin.strip()
    ]
    if browser_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=browser_origins,
            allow_credentials=False,
            allow_methods=["POST", "OPTIONS"],
            allow_headers=["Content-Type", "Idempotency-Key"],
            max_age=600,
        )

    @application.middleware("http")
    async def add_request_id(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        # Configure the deployment's logging formatter to emit these fields as JSON.
        # Do not log bodies, email addresses, phone numbers, or candidate profile URLs.
        logger.info(
            "request_completed",
            extra={"request_id": request_id, "method": request.method, "status": response.status_code},
        )
        return response

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        # Report field paths and error types only; never serialize Pydantic's raw input.
        details = [
            {
                "field": ".".join(str(part) for part in error.get("loc", ())),
                "code": str(error.get("type", "invalid")),
            }
            for error in exc.errors()
        ]
        request_id = getattr(request.state, "request_id", "unknown")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "error": {
                    "code": "invalid_request",
                    "message": "Review the indicated fields and try again.",
                    "details": details,
                    "request_id": request_id,
                }
            },
            headers={"X-Request-ID": request_id},
        )

    @application.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        public_errors = {
            status.HTTP_404_NOT_FOUND: ("not_found", "The requested item was not found."),
            status.HTTP_429_TOO_MANY_REQUESTS: ("rate_limited", "Please wait before trying again."),
            status.HTTP_503_SERVICE_UNAVAILABLE: (
                "service_unavailable",
                "Submission is temporarily unavailable.",
            ),
        }
        code, message = public_errors.get(
            exc.status_code,
            ("request_failed", "We could not complete the request."),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": code, "message": message, "request_id": request_id}},
            headers={**(exc.headers or {}), "X-Request-ID": request_id},
        )

    @application.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        # Keep broadly accessible logs free of exception text and request data.
        logger.error(
            "unhandled_request_error",
            extra={"request_id": request_id, "exception_type": type(exc).__name__},
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "We could not complete the request. Please try again.",
                    "request_id": request_id,
                }
            },
            headers={"X-Request-ID": request_id},
        )

    @application.post(
        "/v1/contact-inquiries",
        status_code=status.HTTP_202_ACCEPTED,
        dependencies=[Depends(rate_limit("contact", limit=5, window_seconds=60))],
    )
    async def create_contact_inquiry(
        payload: ContactRequest,
        request: Request,
        idempotency_key: IdempotencyKey,
        service: Annotated[SubmissionService, Depends(get_submission_service)],
    ) -> dict[str, str]:
        # The trusted Next.js/server adapter should generate a fresh UUIDv4 per
        # submission attempt. The key provides retry safety, never authorization.
        await service.accept_contact_once(payload, idempotency_key)
        return {"status": "accepted", "request_id": request.state.request_id}

    @application.post(
        "/v1/candidate-applications",
        status_code=status.HTTP_202_ACCEPTED,
        dependencies=[Depends(rate_limit("candidate-application", limit=3, window_seconds=60))],
    )
    async def create_candidate_application(
        payload: CandidateApplicationRequest,
        request: Request,
        idempotency_key: IdempotencyKey,
        service: Annotated[SubmissionService, Depends(get_submission_service)],
    ) -> dict[str, str]:
        # The service re-checks that the role is open and enforces idempotency
        # transactionally. Candidate reads/updates require separate identity checks.
        # The trusted Next.js/server adapter should generate a fresh UUIDv4 per
        # attempt; this key is retry metadata, never candidate authorization.
        await service.accept_application_once(payload, idempotency_key)
        return {"status": "accepted", "request_id": request.state.request_id}

    return application


app = create_app()
