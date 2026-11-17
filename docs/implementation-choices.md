# Implementation Choices and Review Notes

## Why these examples

- **FastAPI/Pydantic:** Demonstrates server-side request validation, bounded fields, stable error shapes, rate limiting, and idempotency boundaries. It is a proposed backend example and is not connected to Cynbit.
- **Next.js Server Action:** Demonstrates that a Server Action should call the same trusted business boundary as any other API mutation. Client action IDs are not credentials.
- **Next.js header examples:** `headers.config.ts` shows global transport and browser headers; `proxy.ts` shows nonce-based CSP in report-only mode. CSP must be tested against real script/style and integration requirements. A per-response nonce can require dynamic rendering and reduce static-cache effectiveness; begin with report-only and measure.
- **Redis:** Used only as a shared rate-limit counter with short TTL. Production deployment must account for trusted proxy configuration, Redis availability, key rotation, observability, and abuse thresholds.
- **Outbox payloads:** Keep notification events minimal. Prefer a protected record reference and template/event type over duplicating candidate form data; apply least-privilege worker access and retention to the outbox.

## Recommendations by finding

### OBS-02 — Headers and CSP

Start with `Content-Security-Policy-Report-Only`, inspect browser reports, and inventory script, style, image, font, and connection origins. If centralized reports are needed, configure a same-origin collector and `Reporting-Endpoints`/`report-to` with PII scrubbing. Then enforce a nonce-based policy suitable for the deployed Next.js version. Avoid broad `unsafe-eval` or third-party wildcards as a shortcut. Include `object-src 'none'`, `base-uri 'self'`, `frame-ancestors 'none'` if embedding is not needed, and `form-action 'self'`. Add `X-Content-Type-Options: nosniff`, a deliberate `Referrer-Policy`, and a restrictive `Permissions-Policy`. Preserve HSTS; expand its scope only after subdomain review. Nonce-bearing CSP can require dynamic rendering, so assess the resulting HTML cache behavior. Next.js documents both custom headers and nonce-based CSP behavior: [headers configuration](https://nextjs.org/docs/app/api-reference/config/next-config-js/headers), [CSP guide](https://nextjs.org/docs/14/app/building-your-application/configuring/content-security-policy).

### OBS-03 — CORS

Do not set CORS globally for the marketing site by default. For a browser API that truly needs cross-origin use, allow only expected origins, methods, and headers. If credentials are needed, use explicit origins and `Vary: Origin`; wildcard origin is incompatible with credentialed browser access. Verify preflight and actual route responses in an authorized staging environment.

### OBS-04/05 — Server Actions, validation, and errors

Validate at the server boundary even when the HTML form has `required` and `type="email"`. Enforce body and field count limits, maximum lengths, supported enums, URL schemes, and role state. Use transactionally enforced idempotency, rate limits, and safe error mapping. Next.js specifically advises treating Server Actions like public API endpoints and validating client input: [data security](https://nextjs.org/docs/app/guides/data-security), [mutating data](https://nextjs.org/docs/app/getting-started/mutating-data).

### Candidate data

Minimize initial fields, avoid collecting demographic or exact address information until a defined later need, separate optional demographic reporting from selection, and publish retention/deletion details. Encrypt data in transit and at rest, restrict candidate record reads by role and candidate identity, and redact PII from logs, alerts, and support tooling.

### Spam and duplicate submissions

Use distributed per-IP throttling (the code example uses HMACed IP keys and short TTLs), a short-lived server-issued idempotency token backed by a unique database constraint, and email verification or risk-based challenge when abuse signals justify it. The sample thresholds are illustrative, not a recommendation for a specific production rate. Do not rely solely on CORS, a hidden form field, or a client-side CAPTCHA state. Limit application notifications with an outbox and delivery retries.

### Performance

The evidence supports keeping immutable caching for hash-named assets and confirms Brotli for one HTML response. It does not support database indexes, Redis response caching, connection-pool changes, or queue sizing as current fixes. Those remain architecture options to evaluate only with workload traces and measured bottlenecks.

## External technical references

- [Next.js Data Security](https://nextjs.org/docs/app/guides/data-security)
- [Next.js Authentication](https://nextjs.org/docs/app/guides/authentication)
- [Next.js Mutating Data](https://nextjs.org/docs/app/getting-started/mutating-data)
- [Next.js CSP guide](https://nextjs.org/docs/14/app/building-your-application/configuring/content-security-policy)
- [Next.js response headers configuration](https://nextjs.org/docs/app/api-reference/config/next-config-js/headers)
- [OWASP Input Validation Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html)
- [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)
- [Starlette TestClient](https://www.starlette.io/testclient/)
