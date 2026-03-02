/**
 * Cloudflare Worker — edge proxy for the usaspending-mcp HTTP server.
 *
 * The Python FastMCP server (Streamable HTTP transport) cannot run directly
 * on CF Workers. Deploy it on DigitalOcean App Platform (or any host), then
 * point BACKEND_URL at it. This worker forwards all /mcp traffic — including
 * SSE streams — to the backend with correct session header propagation.
 *
 * Set BACKEND_URL via:
 *   wrangler secret put BACKEND_URL
 *   e.g. https://usaspending-mcp-api-xxxxx.ondigitalocean.app
 */
export default {
  async fetch(request, env) {
    const backend = (env.BACKEND_URL || "").replace(/\/$/, "");
    if (!backend) {
      return new Response(
        JSON.stringify({ error: "BACKEND_URL not configured" }),
        { status: 503, headers: { "Content-Type": "application/json" } }
      );
    }

    const url = new URL(request.url);
    const targetUrl = `${backend}${url.pathname}${url.search}`;

    // Forward headers, preserving MCP session correlation
    const headers = new Headers(request.headers);
    headers.set("X-Forwarded-For", request.headers.get("CF-Connecting-IP") || "");
    headers.delete("Host");

    const upstream = new Request(targetUrl, {
      method: request.method,
      headers,
      body: request.body,
      // Required for SSE streaming (GET /mcp)
      duplex: "half",
    });

    const response = await fetch(upstream);

    // Pass the response through — CF Workers streams SSE transparently
    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: response.headers,
    });
  },
};
