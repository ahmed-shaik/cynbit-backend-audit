"""Shared, short-window rate limiter for a proposed FastAPI deployment."""

from __future__ import annotations

import hashlib
import hmac
import logging
from collections.abc import Awaitable, Callable
from typing import Protocol

from fastapi import HTTPException, Request, status
from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger("assessment_api.rate_limit")


_INCREMENT_WITH_TTL = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return {count, redis.call('TTL', KEYS[1])}
"""


class RateLimiterPort(Protocol):
    async def hit(
        self,
        request: Request,
        *,
        scope: str,
        limit: int,
        window_seconds: int,
    ) -> int: ...

    async def close(self) -> None: ...


class PublicRateLimiter:
    def __init__(self, redis: Redis, fingerprint_key: bytes) -> None:
        if len(fingerprint_key) < 32:
            raise ValueError("RATE_LIMIT_HMAC_KEY must contain at least 32 bytes")
        self._redis = redis
        self._fingerprint_key = fingerprint_key

    async def close(self) -> None:
        await self._redis.aclose()

    async def hit(
        self,
        request: Request,
        *,
        scope: str,
        limit: int,
        window_seconds: int,
    ) -> int:
        # Configure the ASGI server to trust forwarded headers only from known ingress
        # proxies. Never use an arbitrary X-Forwarded-For value as an identity key.
        address = request.client.host if request.client else "unknown"
        digest = hmac.new(
            self._fingerprint_key,
            address.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        key = f"public-rate:v1:{scope}:{digest}"
        try:
            result = await self._redis.eval(_INCREMENT_WITH_TTL, 1, key, window_seconds)
            count, retry_after = int(result[0]), max(1, int(result[1]))
        except RedisError as exc:
            # Fail closed for public mutation endpoints; alert through a redacted
            # operational channel and keep the user-facing response generic.
            logger.error(
                "rate_limit_backend_unavailable",
                extra={"scope": scope, "error_type": type(exc).__name__},
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Submission is temporarily unavailable",
            ) from exc

        if count > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Please wait before trying again",
                headers={"Retry-After": str(retry_after)},
            )
        return count


def rate_limit(scope: str, *, limit: int, window_seconds: int) -> Callable[..., Awaitable[None]]:
    # Example thresholds only. Tune by route, traffic, and abuse telemetry.
    async def enforce(request: Request) -> None:
        limiter: RateLimiterPort = request.app.state.rate_limiter
        await limiter.hit(
            request,
            scope=scope,
            limit=limit,
            window_seconds=window_seconds,
        )

    return enforce
