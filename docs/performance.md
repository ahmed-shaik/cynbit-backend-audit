# Performance Observations and Measurement Limits

## Single-request observations

Measurements below came from one ordinary GET request per page on 2026-11-17. The elapsed time is the command client's end-to-end wait for the response; it is not a server-side timer.

| Resource | Status | Client-observed elapsed time | Decoded body size | Observable delivery details |
|---|---:|---:|---:|---|
| `https://cynbit.in/` | 200 | 841 ms | 100,660 bytes | Vercel; `X-Vercel-Cache: HIT`; `Cache-Control: public, must-revalidate, max-age=0`; `Age: 153633`; 15 linked scripts in returned HTML. |
| `https://www.cynbit.in/contact` | 200 | 156 ms | 64,026 bytes | Vercel cache hit; `Age: 67530` in first sample; `max-age=0, must-revalidate`; a separate request negotiated Brotli. |
| `https://www.cynbit.in/careers/backend-developer-intern` | 200 | 554 ms | 78,315 bytes | `Cache-Control: no-store, must-revalidate, no-cache, max-age=0, private`; Vercel cache miss; Next.js prerender metadata. |
| Contact page bundle | 200 | 413 ms | 24,534 bytes | Hashed `_next/static` bundle; `public, max-age=31536000, immutable`. |
| Careers page bundle | 200 | 140 ms | 28,394 bytes | Hashed `_next/static` bundle; `public, max-age=31536000, immutable`. |

Decoded body sizes are not compressed wire sizes. The Brotli observation was made with a separate GET that advertised `Accept-Encoding: gzip, br`. The page HTML referenced 15 script URLs; only the page-specific contact and careers bundles were fetched and inspected for this phase. No full asset waterfall was captured.

## What the timings mean

- **CDN response time:** Time spent by the CDN/edge to find a cache entry, revalidate it, or fetch from origin and return it. `Age` and Vercel cache headers describe cache state, not backend processing duration.
- **Network latency:** DNS lookup, connection setup, TLS negotiation, routing, and transit contribute to the elapsed time. Geography and transient network conditions were not controlled.
- **Backend processing time:** Application/database work at the origin. It cannot be isolated from these client GET timings. Public page cache hits may avoid origin computation entirely.
- **Browser rendering time:** Parsing, hydration, JavaScript execution, image/font loading, layout, and paint. It was not measured because a DevTools/browser performance trace was unavailable.

## Interpretation

The sample confirms that the observed hashed JS bundles are long-lived cacheable and that Brotli was negotiated for the contact HTML. The differing HTML cache policies are visible, but their intent and effect on freshness are unknown. The role page's `no-store` may be conservative for a dynamic route; no performance problem is established. A single request per page cannot establish average, tail latency, capacity, cache hit ratio, or a bottleneck.

Before tuning, collect repeated measurements from representative locations, record browser navigation and Web Vitals, compare cache hit/miss requests, and correlate request IDs with origin traces and database spans. Do not load-test Cynbit as part of this assessment.
