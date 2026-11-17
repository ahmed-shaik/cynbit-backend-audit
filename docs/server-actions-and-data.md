# Server Actions and Candidate Data Analysis

## What was observable

The contact page's public JavaScript bundle creates a Server Action reference named `submitInquiry`. Its submit handler prevents the default browser submission, creates `FormData`, calls the reference, and shows a success screen when the returned object has `success` set. A non-success result produces a generic message. The careers bundle creates a reference named `submitCandidateApplication`; its handler appends a `jobId` and serializes the education rows into an `educationData` form field before calling it.

This is evidence of a Next.js Server Action client boundary. It is not evidence of the implementation behind either action. No POST was issued, so the actual action URL, headers, request encoding, response status, durable-write behavior, and server validation are unverified. The client action references are not credentials and must not be treated as an access-control mechanism.

## Architectural role and security responsibilities

Next.js Server Actions let a client component invoke asynchronous server-side functions for mutations without defining a separate REST route for each form. Current Next.js documentation describes POST-based invocation, public endpoint exposure, secure action identifiers, and Origin-versus-Host checks. Those are framework behaviors, not a verification of Cynbit's deployed version or configuration. Action identifiers are not credentials, and framework origin checks do not replace validation or record authorization. See [Next.js data security](https://nextjs.org/docs/app/guides/data-security), [Next.js mutating data](https://nextjs.org/docs/app/getting-started/mutating-data), and [Next.js authentication guidance](https://nextjs.org/docs/app/guides/authentication).

For these publicly callable form actions, a suitable server flow is:

1. Enforce request-size, field-count, and content-type limits at the edge/runtime.
2. Parse untrusted `FormData` into a typed schema. Reject missing, repeated, wrong-type, oversized, or out-of-range fields. Do not trust HTML `required` attributes, hidden values, `jobId`, or serialized education JSON.
3. Apply origin/host protections and use HTTPS. Current Next.js documentation describes Server Action Origin-versus-Host checks; Cynbit's deployed version and config were not verified. If a separate API is called, configure its CORS/CSRF boundary independently. CORS is not authorization.
4. For a public application-creation action, no user login may be necessary, but validate that the selected role exists and accepts applications. For any later candidate record read/update action, verify the candidate's authenticated identity and access on every request. A role ID, email address, action ID, or opaque URL alone must not grant access.
5. Enforce abuse controls independently of CSRF protections: a shared per-IP rate limit, email verification for follow-up, and a honeypot or risk-based challenge where warranted. If a keyed email rate limit is justified, use a short-lived keyed digest after validation and explain the processing purpose. Resolve client IP only through explicitly trusted proxies. The FastAPI sample implements the per-IP control only; its limits are illustrative.
6. Make retries safe. Give each form attempt a server-issued idempotency token and enforce uniqueness transactionally so a double click, retry, or timeout does not create duplicate applications or notifications.
7. Persist the application and an email outbox event in one database transaction. Send email asynchronously and retry the outbox; do not make the user-facing response depend on a third-party mail provider being immediately available.
8. Return a minimal result. Do not echo a candidate record or internal error. Log a request/correlation ID and event outcome, not the full form body, resume URL, phone, address, or date of birth.

These are controls to verify or implement, not findings that Cynbit lacks them.

The practical retry contract and transaction pattern are in [idempotency.md](idempotency.md). The FastAPI code demonstrates the API header and injected service contract; it does not claim to implement the database uniqueness or transaction behavior.

## Safe error model

For validation errors, return a stable error code and only field-level messages. For an accepted submission, return a generic receipt and a correlation ID. For unexpected failures, preserve the internal exception in protected telemetry while showing a generic retry/help message to the applicant. Avoid messages such as “this email already has an application” if that would reveal another candidate's state. The client should always leave its pending state in `finally` and must not show success until the service has durably accepted the submission.

## Data minimization assessment

### Initial screening

The public role form asks for name, email, phone, WhatsApp, date of birth, gender, education history, notice period, skills, current city, permanent address, resume/portfolio, LinkedIn, optional professional profile, and an application statement. Several personal/contact fields are required. A first screening decision can usually begin with a smaller set: name, email, role, relevant skills, a short statement, and an optional resume/portfolio link. Current city or work-location eligibility can be optional if it is genuinely required for this role.

### Fields to defer or make optional

- **Date of birth:** Usually not necessary to evaluate an initial technical application. If a later hiring workflow needs it for a defined administrative reason, collect it then with restricted access.
- **Gender:** Not needed to assess technical qualifications. If collected voluntarily for a separate, disclosed aggregate purpose, keep it optional and segregated from screening decisions.
- **Permanent address:** Usually unnecessary before an offer or other defined administrative stage. Defer collection and use a secure channel if later needed.
- **Phone and WhatsApp:** One contact method is generally enough for early screening. Prefer email initially or make phone optional; avoid requiring two phone numbers.
- **Education details:** A concise qualification and graduation status may suffice initially. Detailed scores and multiple qualifications can be requested at a later stage if they affect eligibility.

The form page says submitted information is processed for talent acquisition review. The privacy page describes minimum collection and a way to request copies or deletion, but the page reviewed did not show a retention period or a field-by-field purpose. The apparent mismatch between the broad form and short privacy summary is a transparency opportunity, not proof of a legal violation. The inspection did not establish actual retention, deletion execution, access controls, or vendor processing.

### Proposed staged workflow

| Stage | Suggested fields | Data handling |
|---|---|---|
| Initial application | Name, email, role, skills, short statement; optional resume/portfolio and optional city | Validate and deduplicate; provide purpose, access, retention, and deletion notice at collection. |
| Screening/interview | Preferred contact method, relevant education details, scheduling availability | Collect only for candidates progressing; restrict access to recruiting staff and assigned interviewers. |
| Conditional offer/onboarding | Address, date of birth, and other administrative details only if needed | Use a restricted onboarding workflow, separate from public application intake, with shorter access lists and retention rules. |
| Optional diversity reporting | Optional demographic fields, if there is a clear purpose | Store separately from selection data; restrict access and report only aggregate results. |

Set a documented retention schedule by stage, define deletion from the primary database, outbox/email copies, attachments, and backup expiration, and publish a contact route and expected completion window. This is a design recommendation; the assessment did not verify current retention practices.
