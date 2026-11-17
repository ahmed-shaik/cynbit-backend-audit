from __future__ import annotations

import pytest
from fastapi import HTTPException
from redis.exceptions import RedisError
from starlette.requests import Request
import trio

from examples.fastapi.security import PublicRateLimiter


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, int] = {}
        self.ttls: dict[str, int] = {}

    async def eval(self, script: str, numkeys: int, key: str, window_seconds: int) -> list[int]:
        count = self.values.get(key, 0) + 1
        self.values[key] = count
        self.ttls.setdefault(key, window_seconds)
        return [count, self.ttls[key]]

    async def aclose(self) -> None:
        return None


class FailedRedis(FakeRedis):
    async def eval(self, script: str, numkeys: int, key: str, window_seconds: int) -> list[int]:
        raise RedisError("redis://secret.example.internal/0")


def make_request(ip_address: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "scheme": "https",
            "path": "/v1/contact-inquiries",
            "headers": [],
            "client": (ip_address, 43210),
            "server": ("test.local", 443),
        }
    )


def test_rate_limiter_uses_atomic_counter_and_hides_raw_ip() -> None:
    redis = FakeRedis()
    limiter = PublicRateLimiter(redis, b"k" * 32)  # type: ignore[arg-type]

    first = trio.run(
        lambda: limiter.hit(make_request("203.0.113.10"), scope="contact", limit=3, window_seconds=60)
    )
    second = trio.run(
        lambda: limiter.hit(make_request("203.0.113.10"), scope="contact", limit=3, window_seconds=60)
    )

    assert (first, second) == (1, 2)
    assert len(redis.values) == 1
    assert "203.0.113.10" not in next(iter(redis.values))


def test_rate_limiter_rejects_over_limit_and_reports_remaining_window() -> None:
    redis = FakeRedis()
    limiter = PublicRateLimiter(redis, b"k" * 32)  # type: ignore[arg-type]

    trio.run(lambda: limiter.hit(make_request("203.0.113.11"), scope="contact", limit=1, window_seconds=60))
    with pytest.raises(HTTPException) as caught:
        trio.run(lambda: limiter.hit(make_request("203.0.113.11"), scope="contact", limit=1, window_seconds=60))

    assert caught.value.status_code == 429
    assert caught.value.headers == {"Retry-After": "60"}


def test_rate_limiter_fails_closed_without_echoing_backend_error(caplog: pytest.LogCaptureFixture) -> None:
    limiter = PublicRateLimiter(FailedRedis(), b"k" * 32)  # type: ignore[arg-type]

    with pytest.raises(HTTPException) as caught:
        trio.run(lambda: limiter.hit(make_request("203.0.113.12"), scope="contact", limit=3, window_seconds=60))

    assert caught.value.status_code == 503
    assert "secret.example.internal" not in caplog.text
    assert "203.0.113.12" not in caplog.text
