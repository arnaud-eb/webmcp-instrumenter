// Cloudflare Worker — WebMCP invocation logging sink (US4, T029/T030).
//
// Two paths, deliberately minimal (Principle V):
//   POST /events  — insert-only write path for the generated logger.js. Best-effort:
//                   the client ignores the response (Principle III / FR-010), and a value
//                   can never be stored because the table has no column for one (Principle II).
//   GET  /report  — scoped, operator-only read path for `report`. MAY fail loudly.

interface Env {
  DB: D1Database;
  REPORT_TOKEN?: string;
}

// Public insert endpoint — the client posts cross-origin, so answer preflight permissively.
// There is nothing to protect: the table stores no secrets and no values.
const CORS: Record<string, string> = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: CORS });
    }
    if (url.pathname === "/events" && request.method === "POST") {
      return handleEvent(request, env);
    }
    if (url.pathname === "/report" && request.method === "GET") {
      return handleReport(request, env, url);
    }
    return new Response("not found", { status: 404 });
  },
};

// Every response on the write path is a 202 the client ignores — including on bad input. We
// never surface an error to the host page, and we never store a row we're unsure about.
const ACCEPTED = () => new Response(null, { status: 202, headers: CORS });

async function handleEvent(request: Request, env: Env): Promise<Response> {
  let body: Record<string, unknown>;
  try {
    body = (await request.json()) as Record<string, unknown>;
  } catch {
    return ACCEPTED();
  }

  // Whitelist exactly the five allowed fields; drop everything else so an unexpected
  // value-bearing field can never reach storage (Principle II).
  const site = typeof body.site === "string" ? body.site : null;
  const toolName = typeof body.tool_name === "string" ? body.tool_name : null;
  const ts = typeof body.timestamp === "string" ? body.timestamp : null;
  const success = body.success ? 1 : 0;
  const paramKeys = Array.isArray(body.param_keys) ? body.param_keys : [];

  // Each param key MUST be a string. A non-string entry (e.g. {"name": "Ada"}) means the
  // client tried to send a value — reject the whole row rather than risk storing PII.
  const keysAreNames = paramKeys.every((k) => typeof k === "string");
  if (!site || !toolName || !ts || !keysAreNames) {
    return ACCEPTED();
  }

  try {
    await env.DB.prepare(
      "INSERT INTO invocations (site, tool_name, ts, success, param_keys) VALUES (?, ?, ?, ?, ?)",
    )
      .bind(site, toolName, ts, success, JSON.stringify(paramKeys))
      .run();
  } catch {
    // Storage failure must not surface to the client either.
    return ACCEPTED();
  }
  return ACCEPTED();
}

async function handleReport(request: Request, env: Env, url: URL): Promise<Response> {
  // Operator-only, scoped by a bearer token that lives only server-side (wrangler secret).
  const token = (request.headers.get("Authorization") || "").replace(/^Bearer\s+/i, "");
  if (!env.REPORT_TOKEN || token !== env.REPORT_TOKEN) {
    return new Response("unauthorized", { status: 401 });
  }
  const from = url.searchParams.get("from");
  const to = url.searchParams.get("to");
  if (!from || !to) {
    return new Response("from and to (ISO dates) are required", { status: 400 });
  }
  const rows = await env.DB.prepare(
    "SELECT site, tool_name, ts, success, param_keys FROM invocations " +
      "WHERE ts >= ? AND ts <= ? ORDER BY ts",
  )
    .bind(from, to)
    .all();
  return Response.json({ events: rows.results ?? [] });
}
