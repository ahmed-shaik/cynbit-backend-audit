# Idempotency and Duplicate Submission Handling

## Why it matters

Browsers, proxies, and users can retry after a timeout even when the server committed the first request. A double-click can also send two concurrent submissions. Without idempotency, the same action may create duplicate database rows or email notifications. Idempotency is a retry-safety mechanism; it is not authentication, authorization, or spam prevention.

## Recommended contract

1. Generate a high-entropy idempotency token for a submission attempt. Prefer issuing it with the form or server action and binding it to the operation and role. Do not use the token as permission to read an application.
2. The trusted service computes a keyed HMAC of the canonical, validated request payload. Do not log the token, raw payload, or digest. A keyed digest avoids storing a simple hash of low-entropy personal data.
3. Scope the token by operation and store it under a database uniqueness constraint. Same key + same request returns the stored receipt. Same key + different request returns a generic conflict. A new intentional submission gets a new key and is subject to the product's explicit duplicate policy.
4. In one database transaction, create the idempotency record, business record, and outbox event; store the minimal response receipt before commit. If any insert fails, roll back all writes. Keep the outbox payload to a notification type and protected record reference where possible, not a copy of the full candidate form; expire or delete delivered events under the retention policy.
5. Return the accepted response only after commit. On retry, return the saved receipt and do not create another row or outbox event. The worker should also process each outbox event idempotently.

## PostgreSQL shape

```sql
CREATE TABLE idempotency_requests (
  operation       text        NOT NULL,
  idempotency_key uuid        NOT NULL,
  request_hmac    bytea       NOT NULL,
  response_json   jsonb,
  created_at      timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (operation, idempotency_key)
);

CREATE TABLE candidate_applications (
  id              uuid        PRIMARY KEY,
  idempotency_key uuid        NOT NULL UNIQUE,
  role_id         text        NOT NULL,
  state           text        NOT NULL,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE email_outbox (
  event_id        uuid        PRIMARY KEY,
  idempotency_key uuid        NOT NULL UNIQUE,
  event_type      text        NOT NULL,
  payload         jsonb       NOT NULL,
  created_at      timestamptz NOT NULL DEFAULT now(),
  delivered_at    timestamptz
);
```

## Transaction pseudocode

```text
BEGIN
  INSERT idempotency_requests(operation, key, request_hmac)
    ON CONFLICT DO NOTHING
  SELECT request_hmac, response_json
    FROM idempotency_requests
    WHERE operation = :operation AND idempotency_key = :key
    FOR UPDATE

  if stored HMAC differs:
    ROLLBACK; return generic 409 conflict
  if response_json exists:
    COMMIT; return stored acceptance receipt

  verify role is open and business rules pass
  INSERT application with unique idempotency_key
  INSERT one email_outbox event with unique idempotency_key
  UPDATE idempotency_requests with minimal receipt
COMMIT
return receipt
```

The unique key serializes concurrent retries: one request wins the insert; a concurrent request waits on the constraint and then reads the committed receipt. If the transaction rolls back, a retry can perform the work. If the key is reused with a changed payload, reject it. Keep the database constraint as the final guarantee; an in-memory cache or frontend disabled button is insufficient.

For contact inquiries, use the same retry-safety pattern but a separate operation scope and retention policy. Do not impose a permanent unique constraint on email alone: a person may legitimately submit a new inquiry or application later. A separate duplicate-application rule should be explicit, role-scoped, and based on verified identity where appropriate.

The FastAPI example exposes an idempotency header and service contract but intentionally does not implement a production database adapter. The SQL above is a design example; concurrency and isolation choices must be reviewed for the chosen database.
