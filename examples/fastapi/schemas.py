"""Typed request contracts for a proposed public contact/recruitment API."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, field_validator


ShortText = Annotated[str, Field(min_length=1, max_length=120)]
Skill = Annotated[str, Field(min_length=1, max_length=48)]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ContactRequest(InputModel):
    full_name: ShortText
    email: EmailStr
    company: Annotated[str, Field(max_length=120)] | None = None
    industry: Annotated[str, Field(max_length=80)] | None = None
    message: Annotated[str, Field(min_length=10, max_length=4_000)]


class CandidateApplicationRequest(InputModel):
    """Initial-stage data only; sensitive later-stage fields are intentionally omitted."""

    job_id: Annotated[str, Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")]
    full_name: ShortText
    email: EmailStr
    skills: Annotated[list[Skill], Field(min_length=1, max_length=12)]
    statement: Annotated[str, Field(min_length=20, max_length=3_000)]
    portfolio_url: HttpUrl | None = None
    linkedin_url: HttpUrl | None = None

    @field_validator("portfolio_url", "linkedin_url")
    @classmethod
    def require_https(cls, value: HttpUrl | None) -> HttpUrl | None:
        if value is None:
            return None
        if value.scheme != "https" or value.username is not None or value.password is not None:
            raise ValueError("profile links must use HTTPS and contain no credentials")
        if len(str(value)) > 2_048:
            raise ValueError("profile links must be 2048 characters or fewer")
        return value
