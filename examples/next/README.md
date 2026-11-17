# Next.js examples

These snippets assume a Next.js 16 App Router project. They are examples, not a drop-in patch for Cynbit.

- Merge `headers.config.ts` into the application's existing Next config. Confirm the platform also applies HSTS to every relevant HTTPS response.
- `proxy.ts` demonstrates a per-response nonce and a `Content-Security-Policy-Report-Only` response. Review actual inline scripts/styles and third-party origins first. The inspected Cynbit page includes an inline style attribute, so policy reports should be reviewed before enforcement. A nonce can require dynamic rendering and change full-page caching.
- Report-only violations appear in developer tools. For centralized collection, add a protected same-origin reporting endpoint and `Reporting-Endpoints`/`report-to` configuration; scrub report fields and do not treat reports as trusted input.
- `server-action.ts` uses fail-closed adapter ports under `server-only/`. They do not provide persistence or rate limiting by themselves. Register implementations backed by durable database/outbox transactions and shared anti-spam controls during server bootstrap before wiring this example into an application.
