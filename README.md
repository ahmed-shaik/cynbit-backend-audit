# Cynbit Backend Assessment — Technical Review Package

This assessment package is based on passive public-page inspection and the evidence listed in `docs/findings-matrix.md`. It does not describe Cynbit's verified private backend implementation, and none of the proposed code is connected to Cynbit systems.

## Package contents

- `docs/findings-matrix.md` — consolidated observations, evidence, provisional severity, confidence, risk, and recommendation.
- `docs/report-draft.md` — integrated report draft with executive summary, scope, key findings, and conclusion.
- `docs/server-actions-and-data.md` — Server Actions analysis and a staged, data-minimizing recruitment flow.
- `docs/idempotency.md` — retry and duplicate-submission behavior with a PostgreSQL transaction pattern.
- `docs/performance.md` — one-request measurements and their limits.
- `docs/proposed-architecture.md` — recommended architecture diagram and boundaries.
- `docs/implementation-choices.md` — security recommendation map and sample-code rationale.
- `examples/fastapi/` — illustrative backend validation, rate-limit, safe-error, and idempotency boundaries.
- `examples/next/` — illustrative Next.js global headers, nonce/report-only CSP, and a Server Action boundary.
- `tests/` — unit and route-contract tests using in-memory fakes; these do not verify production database concurrency.

## Key findings and proposed architecture

The inspected HTML responses showed HTTPS redirection and HSTS, while sampled responses lacked CSP and several other browser-policy headers. The public careers form requires more personal information than appears necessary for an initial technical screen. The client bundles expose Next.js Server Action references, but no action was invoked and no server behavior was verified. Performance values are single-request observations only. No vulnerability was demonstrated.

The recommended architecture separates public contact inquiries from candidate applications. Contact intake is public and does not require candidate authentication. Candidate status access is identity-verified and application-scoped. Both flows use validation, abuse controls, database transactions, an email outbox, and PII-redacted observability; see `docs/proposed-architecture.md`.

## Repository layout

```text
cynbit-backend-audit/
├── .gitignore
├── README.md
├── docs/
│   ├── findings-matrix.md
│   ├── idempotency.md
│   ├── implementation-choices.md
│   ├── performance.md
│   ├── proposed-architecture.md
│   ├── report-draft.md
│   └── server-actions-and-data.md
├── examples/
│   ├── __init__.py
│   ├── fastapi/
│   │   ├── __init__.py
│   │   ├── app.py
│   │   ├── requirements.txt
│   │   ├── schemas.py
│   │   └── security.py
│   └── next/
│       ├── headers.config.ts
│       ├── proxy.ts
│       ├── README.md
│       ├── server-action.ts
│       └── server-only/
│           ├── abuse-controls.ts
│           ├── application-service.ts
│           ├── request-context.ts
│           └── types.ts
├── requirements-dev.txt
└── tests/
    ├── test_api.py
    ├── test_rate_limiter.py
    └── test_schemas.py
```

## Scope and method

The inspection used ordinary GET requests for the public home, contact, and backend intern pages, followed by GET requests for JavaScript bundles directly referenced by the contact and role pages. No forms were submitted, no accounts were created, and no candidate records were accessed. Response timing is from one request per page and is not a benchmark. The browser helper could not verify the active Chrome URL, so a DevTools network trace was unavailable.

## Ethical testing statement

Only ordinary public GET requests and directly linked public assets were inspected. No forms were submitted, accounts created, private records accessed, crafted payloads sent, or load tests performed. This package contains no production credentials and has not been published or submitted.

## Technologies and dependencies

- Report and diagrams: Markdown and Mermaid.
- Backend examples: Python, FastAPI, Pydantic, Redis.
- Next.js examples: TypeScript, Next.js, and Zod.
- Tests: pytest, FastAPI `TestClient`, HTTPX2, and Trio. Test doubles keep tests independent of a live Redis, database, or email service.

The Next.js files are integration examples for an existing Next.js 16 App Router application; they are not a standalone Node project because the application-specific server-only adapters are intentionally omitted. Add Zod to that application's dependencies before using `server-action.ts`.

## Installation and tests

From this directory, create a virtual environment and install the development requirements:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pytest
```

To start the FastAPI boundary example after wiring a `SubmissionService` adapter and Redis:

```powershell
$env:REDIS_URL = "redis://localhost:6379/0"
$env:RATE_LIMIT_HMAC_KEY = "<locally generated random value of at least 32 bytes>"
python -m uvicorn examples.fastapi.app:app --reload
```

The FastAPI app requires `REDIS_URL` and a 32-byte-or-longer `RATE_LIMIT_HMAC_KEY` at startup. Its submission-service adapter is intentionally not implemented, so it returns a generic 503 until a durable service is wired in. It is not a live application or a Cynbit integration.

## Limitations

The scope and technical limitations are detailed in [`docs/report-draft.md`](docs/report-draft.md#limitations) and [`docs/findings-matrix.md`](docs/findings-matrix.md#evidence-limits). No authenticated portal, Server Action submission, private source, database, or production logs were inspected. The tests exercise schemas, rate limiting, and route behavior with in-memory fakes; they do not validate a production database transaction, email provider, or deployment configuration.

Primary public sources:

- [Cynbit home](https://cynbit.in/)
- [Cynbit contact page](https://www.cynbit.in/contact)
- [Cynbit backend intern role](https://www.cynbit.in/careers/backend-developer-intern)
- [Cynbit privacy policy](https://www.cynbit.in/privacy)
- [Contact page client bundle](https://www.cynbit.in/_next/static/chunks/app/%28marketing%29/contact/page-d61cb94b605d803b.js)
- [Careers page client bundle](https://www.cynbit.in/_next/static/chunks/app/%28marketing%29/careers/%5Bslug%5D/page-534c6ed015788338.js)

## Review boundary

This package has not been published, pushed to GitHub, or submitted to the assessment portal. The example code is educational scaffolding and needs environment-specific review before production use.

The FastAPI example defines a submission-service interface but intentionally does not include a database adapter, email provider, or deployment secrets. It is not ready to accept real applications until those components, retention rules, and authorization policy are implemented and reviewed.

The Next.js action example also references app-specific server-only adapters that are described in `examples/next/README.md` and are not included here.

---

## AI Transparency Disclosure

This assessment was prepared with the assistance of AI tools, which supported research, technical analysis, documentation, and implementation examples. The findings, recommendations, and code were reviewed and refined throughout the process.

This disclosure is provided to ensure transparency regarding the use of AI in this project.
