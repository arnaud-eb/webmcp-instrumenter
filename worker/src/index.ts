// Cloudflare Worker — WebMCP invocation logging sink.
// SCAFFOLD STUB (P1 MVP). The insert-only POST /events endpoint and the D1 read
// path are implemented in the US4 phase (T028–T031). See
// specs/001-webmcp-instrumenter/contracts/logging-endpoint.md for the contract.

export default {
  async fetch(_request: Request): Promise<Response> {
    return new Response("webmcp-logger: not yet implemented (US4)", { status: 501 });
  },
};
