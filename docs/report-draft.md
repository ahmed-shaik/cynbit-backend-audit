# Cynbit Backend Developer Assessment — Draft Report

**Prepared for:** Ahmed Shaik  
**Assessment date:** 17 November 2026  
**Scope:** Passive inspection of public pages and directly linked client bundles; proposed architecture and controls are clearly labeled as recommendations.

## Executive summary

This review examined Cynbit's public homepage, contact page, backend developer intern role page, selected response headers, and the contact/careers client bundles. It used ordinary GET requests only. No form was submitted, no login was attempted, and no private candidate record was accessed.

Observed delivery evidence points to Next.js hosted on Vercel. Public form bundles reference two Server Actions, `submitInquiry` and `submitCandidateApplication`; this exposes the client-side mutation boundary but does not reveal the server implementation. HTTP redirects to HTTPS, sampled pages return HSTS, and hash-named static bundles use long-lived immutable caching. Sampled HTML responses lacked several common browser hardening headers. The public role form requests date of birth, gender, permanent address, phone, and WhatsApp as required fields, which is a data-minimization opportunity for initial screening.

No exploitable vulnerability was demonstrated. Server-side validation, authorization, cookies, persistence, API response contracts, duplicate handling, rate limits, retention execution, and backend performance remain unverified. The highest-value next steps are to verify server-side action controls from source or staging, reduce the initial candidate form to screening needs, add tested browser security policies, and collect repeatable browser/origin performance measurements before optimization.

## Scope and method

The reviewed resources and the exact observations are catalogued in [the findings matrix](findings-matrix.md). Three pages and two directly referenced page bundles were fetched with ordinary GET requests. A standard compressed contact-page GET was used to observe Brotli negotiation, and a normal HTTP homepage request was used to observe the HTTPS redirect. Measurements are single-request client observations, not a benchmark.

The Chrome helper could not verify the active browser URL, so no DevTools waterfall, cookie jar, or browser rendering trace was obtained. The assessment did not inspect the candidate progress portal or submit any form. Public policy statements are reported as statements on the site, not independently validated backend facts.

## Limitations

- No forms or Server Actions were invoked; request payloads, action response codes, and server-side validation were not observed.
- No source repository, database, production configuration, logs, authenticated candidate portal, or private candidate data was inspected.
- No crafted requests, vulnerability tests, load tests, or repeated performance runs were performed.
- The browser helper could not confirm the active Chrome URL, preventing DevTools capture. Timings are client-observed single-request durations, not backend or browser-render timings.
- The examples illustrate recommendations. The FastAPI persistence/email service and the Next.js server-only adapters are deliberately not implemented. Tests use in-memory fakes and do not prove database transaction or production behavior.
- No legal compliance determination is made. The form and policy text support only a data-minimization and transparency discussion.

## Findings

The consolidated matrix in [findings-matrix.md](findings-matrix.md) separates verified observations from potential risks and recommendations. Summary:

1. **Transport and delivery:** HTTP redirects to HTTPS; sampled HTTPS responses include two-year HSTS. Response and asset evidence identifies Next.js/Vercel but does not establish the database or backend services.
2. **Security headers:** CSP, `nosniff`, framing, referrer, and permissions policies were absent from sampled HTML headers. This is a low-priority defense-in-depth recommendation, not a confirmed vulnerability.
3. **CORS:** Wildcard ACAO was observed on the homepage only. That is not proof of private data exposure; scope and route consistency should be reviewed.
4. **Server Actions:** Client bundles reference form actions and construct FormData. No action invocation occurred, so wire requests and server behavior are unknown.
5. **Client validation and errors:** Native required/email checks are present. A contact-action rejection may leave the UI pending because the visible handler has no `finally`; this was inferred from code and not exercised.
6. **Candidate data:** Required demographic/contact/address fields appear broader than initial technical screening would usually require. This is a privacy design concern, not a legal finding.
7. **Performance:** Hash-named assets use immutable caching and one contact request negotiated Brotli. Single-request timings do not demonstrate a bottleneck.
8. **Authentication/cookies:** No `Set-Cookie` was observed on sampled HTML responses; candidate authentication and authorization were outside scope.

## Server Action analysis

The public bundles identify `submitInquiry` and `submitCandidateApplication` as Next.js Server Action references. Next.js describes Server Actions as server-side mutation functions invoked over a network request; current documentation says they use POST and should be treated as public endpoints. The action identifier is not authorization. Framework-origin protections help mitigate cross-site calls, but they do not validate business inputs, prove applicant identity, prevent spam, or make writes idempotent. The deployed Next.js version and its action configuration were not verified.

For a proposed flow, each action should parse the full request into a strict schema, verify role status, apply rate limits, use idempotency tied to a durable unique constraint, and persist the submission with an outbox event in one transaction. Application creation may be public; candidate record reads and updates must enforce identity and record-level access every time. See [the detailed action and data analysis](server-actions-and-data.md).

## Candidate data minimization

Initial screening can begin with name, email, role, relevant skills, a short application statement, and optional portfolio/resume. Date of birth, gender, and permanent address do not appear necessary for an initial technical screen based on the public page alone; defer them unless a later, stated process need exists. Consider requiring only one contact method. If demographic fields are collected for a separate voluntary purpose, separate them from selection decisions.

The public privacy policy describes minimal collection and provides a way to request a copy or deletion, but no retention period was visible in the reviewed text. Publish purpose and retention information at collection, define deletion across the database, outbox, attachments, and provider copies, and state a response timeline. See [the staged workflow](server-actions-and-data.md).

## Performance summary

One ordinary GET per page measured 841 ms for the homepage, 156 ms for contact, and 554 ms for the role page. These values combine DNS, TLS, network, CDN, and client effects; they are not origin processing or browser-render time. A separate contact GET negotiated Brotli. Hash-named page bundles returned `public, max-age=31536000, immutable`; page HTML had different cache policies. See [performance notes](performance.md) for sizes and limits.

No database caching, indexing, pooling, or queue optimization is recommended as a current fix because no backend bottleneck was measured. Collect representative repeated browser and origin traces first.

## Proposed architecture and implementation

The diagram in [proposed-architecture.md](proposed-architecture.md) is a recommendation, not a claim about Cynbit's production architecture. It separates public inquiries from candidate applications and applies candidate verification and record-level authorization only where appropriate. The retry and duplicate-submission contract is in [idempotency.md](idempotency.md). Examples are in `examples/fastapi/` and `examples/next/`; see [implementation choices](implementation-choices.md) for their boundaries and review notes.

## Conclusion

The passive evidence supports a careful, bounded assessment: a Next.js/Vercel delivery surface with public Server Action references and a broad candidate intake form. The main opportunities are to verify action-side controls, make early-stage data collection smaller and more transparent, and add measured browser security policies. Backend architecture claims and vulnerability claims should wait for authorized source review or a staging environment.
