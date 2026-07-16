-- WebMCP invocation logging sink — D1 schema (US4, T028).
-- Records param KEY names only; there is deliberately NO column for parameter
-- values (Constitution Principle II / FR-009). A value simply has nowhere to go.

CREATE TABLE IF NOT EXISTS invocations (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  site       TEXT NOT NULL,
  tool_name  TEXT NOT NULL,
  ts         TEXT NOT NULL,          -- ISO-8601 UTC
  success    INTEGER NOT NULL,       -- 0/1
  param_keys TEXT NOT NULL           -- JSON array of key names, no values
);

-- The report queries by date range, grouped by site + tool.
CREATE INDEX IF NOT EXISTS idx_invocations_ts ON invocations (ts);
CREATE INDEX IF NOT EXISTS idx_invocations_site_tool ON invocations (site, tool_name);
