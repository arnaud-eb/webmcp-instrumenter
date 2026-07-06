# Logging Endpoint Contract: Cloudflare Worker + D1

The generated `logger.js` posts one invocation event per agent tool call. The Worker is the
only backend in the system and is intentionally minimal (Principle V).

## Write path — `POST /events`

**Request body** (application/json):

```json
{
  "site": "example.com",
  "tool_name": "submit_contact_form",
  "timestamp": "2026-07-06T10:00:00Z",
  "success": true,
  "param_keys": ["name", "email", "message"]
}
```

- `param_keys` = key names ONLY. The endpoint MUST reject (or ignore) any unexpected field
  that could carry values — the D1 table has no column for values (Principle II / FR-009).
- **Insert-only.** No update/delete/read on this path. No auth secret embedded in the
  client snippet beyond a public write token scoped to insert (Principle II — no secrets that
  matter if leaked).

**Response**: `202 Accepted` (or `204`). The client **ignores the response entirely**.

**Client contract (critical — Principle III / FR-010)**: the POST is fire-and-forget. Network
error, timeout, non-2xx, or CORS failure MUST be swallowed. The agent's tool call and the end
user's interaction succeed regardless. The logger never throws into host-page code.

## D1 schema (`worker/schema.sql`)

```sql
CREATE TABLE IF NOT EXISTS invocations (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  site       TEXT NOT NULL,
  tool_name  TEXT NOT NULL,
  ts         TEXT NOT NULL,          -- ISO-8601 UTC
  success    INTEGER NOT NULL,       -- 0/1
  param_keys TEXT NOT NULL           -- JSON array of key names, no values
);
```

## Read path — used by `report` only

- A scoped read endpoint (or direct D1 query via `wrangler`) returning rows in a date range.
- Not exposed to the client snippet. Operator-run; may fail loudly (unlike the write path).

## Reachability requirement (FR-016)

Cloudflare Workers + D1 free tier does not auto-pause on inactivity, so the sink stays
reachable across the full 4–6 week window without keep-warm hacks. This is the reason it was
chosen over Supabase during clarify.
