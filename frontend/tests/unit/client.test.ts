import { beforeEach, describe, expect, it, vi } from "vitest";
import { fetchAll, request, walkPages } from "@shared/api/client";
import { ApiError, TransportError } from "@shared/api/errors";

/** Build a Response-like object for the fetch mock. */
function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: () => Promise.resolve(body === undefined ? "" : JSON.stringify(body)),
  } as Response;
}

describe("api client", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  it("returns the parsed body on success", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({ id: "abc" }));
    await expect(request<{ id: string }>("/api/demo/notes/")).resolves.toEqual({ id: "abc" });
  });

  it("never sends a client-asserted identity header", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({}));
    await request("/api/demo/notes/");
    const [, init] = vi.mocked(fetch).mock.calls[0]!;
    const headers = (init?.headers ?? {}) as Record<string, string>;
    const names = Object.keys(headers).map((name) => name.toLowerCase());
    for (const forbidden of ["x-school-id", "x-actor-id", "x-role", "x-auth-level"]) {
      expect(names).not.toContain(forbidden);
    }
  });

  it("throws ApiError carrying the envelope for a business failure", async () => {
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse(
        {
          code: "action_denied",
          message_key: "error.action_denied",
          request_id: "req-9",
          field_errors: [],
        },
        403,
      ),
    );
    const error = await request("/api/demo/notes/").catch((caught: unknown) => caught);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).code).toBe("action_denied");
    expect((error as ApiError).requestId).toBe("req-9");
  });

  it("throws TransportError when a failure has no envelope", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({ detail: "gateway" }, 502));
    await expect(request("/api/demo/notes/")).rejects.toBeInstanceOf(TransportError);
  });

  it("throws TransportError when the body is not JSON", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: false,
      status: 500,
      text: () => Promise.resolve("<html>oops</html>"),
    } as Response);
    await expect(request("/api/demo/notes/")).rejects.toBeInstanceOf(TransportError);
  });

  it("throws TransportError when the request never completes", async () => {
    vi.mocked(fetch).mockRejectedValue(new Error("offline"));
    await expect(request("/api/demo/notes/")).rejects.toBeInstanceOf(TransportError);
  });

  it("walks every cursor page exactly once", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(jsonResponse({ items: [{ id: "1" }, { id: "2" }], next_cursor: "c1" }))
      .mockResolvedValueOnce(jsonResponse({ items: [{ id: "3" }], next_cursor: null }));
    await expect(fetchAll<{ id: string }>("/api/demo/notes/")).resolves.toEqual([
      { id: "1" },
      { id: "2" },
      { id: "3" },
    ]);
    expect(vi.mocked(fetch)).toHaveBeenCalledTimes(2);
  });

  it("stops and reports when a cursor never advances", async () => {
    // A server bug that returns the same cursor forever must not spin in the
    // user's browser.
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse({ items: [{ id: "1" }], next_cursor: "stuck" }),
    );
    const iterate = async () => {
      let pages = 0;
      for await (const page of walkPages("/api/demo/notes/", { maxPages: 3 })) {
        pages += page.length;
      }
      return pages;
    };
    await expect(iterate()).rejects.toThrow(/does not advance/);
  });

  it("sends the cursor and page size as query parameters", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({ items: [], next_cursor: null }));
    await request("/api/demo/notes/", { query: { cursor: "abc", page_size: 10 } });
    const [url] = vi.mocked(fetch).mock.calls[0]!;
    // fetch's first argument is typed string | URL | Request. The client always
    // passes a string; narrow each case explicitly rather than relying on
    // stringification, which is meaningless for a Request.
    const requested =
      typeof url === "string" ? url : url instanceof URL ? url.href : url.url;
    expect(requested).toContain("cursor=abc");
    expect(requested).toContain("page_size=10");
  });
});
