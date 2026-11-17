from __future__ import annotations

import pytest
from pydantic import ValidationError

from examples.fastapi.schemas import CandidateApplicationRequest, ContactRequest


def test_contact_schema_accepts_bounded_contact_message() -> None:
    payload = ContactRequest(
        full_name="Ahmed Shaik",
        email="ahmed@example.com",
        message="Please contact me about backend services.",
    )

    assert payload.email == "ahmed@example.com"
    assert payload.company is None


def test_candidate_schema_rejects_extra_sensitive_fields() -> None:
    with pytest.raises(ValidationError):
        CandidateApplicationRequest(
            job_id="backend-intern",
            full_name="Applicant Name",
            email="applicant@example.com",
            skills=["Python"],
            statement="I would like to apply for this backend role.",
            date_of_birth="2004-01-01",
        )


def test_candidate_schema_requires_https_profile_links() -> None:
    with pytest.raises(ValidationError):
        CandidateApplicationRequest(
            job_id="backend-intern",
            full_name="Applicant Name",
            email="applicant@example.com",
            skills=["Python"],
            statement="I would like to apply for this backend role.",
            portfolio_url="http://portfolio.example.com",
        )


def test_candidate_schema_rejects_credentials_in_profile_url() -> None:
    with pytest.raises(ValidationError):
        CandidateApplicationRequest(
            job_id="backend-intern",
            full_name="Applicant Name",
            email="applicant@example.com",
            skills=["Python"],
            statement="I would like to apply for this backend role.",
            portfolio_url="https://user:password@portfolio.example.com",
        )


def test_candidate_schema_rejects_oversized_statement() -> None:
    with pytest.raises(ValidationError):
        CandidateApplicationRequest(
            job_id="backend-intern",
            full_name="Applicant Name",
            email="applicant@example.com",
            skills=["Python"],
            statement="x" * 3_001,
        )
