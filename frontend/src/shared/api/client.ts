/**
 * The one HTTP client every feature uses.
 *
 * Responsibilities, none of which a feature should reimplement:
 *   - resolve the API base URL, which is allocated dynamically per stack
 *   - never send a client-asserted identity header; the server derives identity
 *   - turn a non-2xx response into an ApiError carrying the frozen envelope
 *   - walk cursor pages without exposing the cursor format
 */

import { ApiError, TransportError, isErrorEnvelope } from "./errors";

/** One page of a collection. Mirrors contracts/common/collection.schema.json. */
export interface Collection<Item> {
  readonly items: readonly Item[];
  readonly next_cursor: string | null;
}

/**
 * Resolve the API base URL.
 *
 * `scripts/dev.py up` allocates the API port and prints it; Vite passes it
 * through as VITE_SCHOOL_API_URL. Falls back to a same-origin relative base so
 * that a production build behind one hostname needs no configuration.
 */
export function apiBaseUrl(): string {
  // Typed explicitly: import.meta.env is `any`-ish, and letting that spread into
  // the return type would silently disable checking at every call site.
  const environment = import.meta.env as Record<string, string | undefined>;
  const configured = environment["VITE_SCHOOL_API_URL"];
  return typeof configured === "string" && configured.length > 0
    ? configured.replace(/\/$/, "")
    : "";
}

/** Headers a browser request must never send. Identity is server-derived. */
const FORBIDDEN_HEADERS = [
  "x-school-id",
  "x-actor-id",
  "x-role",
  "x-roles",
  "x-relationship",
  "x-auth-level",
  "x-persona",
] as const;

interface RequestOptions {
  readonly method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  readonly body?: unknown;
  readonly query?: Record<string, string | number | undefined>;
  readonly signal?: AbortSignal;
  /**
   * Extra headers, for a module that needs one the shared client does not know
   * about -- M01 echoes the double-submit CSRF token here. Identity headers remain
   * forbidden and are rejected below regardless of what a caller passes.
   */
  readonly headers?: Record<string, string>;
}

/**
 * Perform one API call and return the parsed body.
 *
 * Throws ApiError when the server returned a well-formed envelope, and
 * TransportError otherwise. Never returns a partially-successful result: a
 * caller that gets a value knows the call succeeded.
 */
export async function request<Result>(
  path: string,
  options: RequestOptions = {},
): Promise<Result> {
  const { method = "GET", body, query, signal, headers: extraHeaders } = options;

  const url = new URL(`${apiBaseUrl()}${path}`, globalThis.location?.href ?? "http://127.0.0.1");
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined) url.searchParams.set(key, String(value));
  }

  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(extraHeaders ?? {}),
  };
  if (body !== undefined) headers["Content-Type"] = "application/json";

  // Defence in depth. The server REJECTS these outright; this catches a caller
  // trying to set one via `headers`, which is now an open door for CSRF tokens.
  // Compared case-insensitively, because HTTP header names are.
  const lowercased = new Set(Object.keys(headers).map((name) => name.toLowerCase()));
  for (const forbidden of FORBIDDEN_HEADERS) {
    if (lowercased.has(forbidden)) {
      throw new Error(`refusing to send client-asserted identity header: ${forbidden}`);
    }
  }

  let response: Response;
  try {
    const init: RequestInit = {
      method,
      headers,
      credentials: "same-origin",
    };
    if (body !== undefined) init.body = JSON.stringify(body);
    if (signal) init.signal = signal;
    response = await fetch(url.toString(), init);
  } catch (cause) {
    throw new TransportError(
      `request to ${path} failed before a response arrived: ${String(cause)}`,
    );
  }

  if (response.status === 204) return undefined as Result;

  let parsed: unknown;
  const text = await response.text();
  try {
    parsed = text.length > 0 ? JSON.parse(text) : undefined;
  } catch {
    throw new TransportError(
      `response from ${path} was not JSON (status ${response.status})`,
      response.status,
    );
  }

  if (!response.ok) {
    if (isErrorEnvelope(parsed)) {
      throw new ApiError(response.status, parsed);
    }
    throw new TransportError(
      `request to ${path} failed with status ${response.status} and no error envelope`,
      response.status,
    );
  }

  return parsed as Result;
}

/**
 * Walk every page of a collection, following next_cursor.
 *
 * `maxPages` is a hard stop. A server bug that returns a non-advancing cursor
 * would otherwise loop forever in a user's browser; failing loudly is better.
 */
export async function* walkPages<Item>(
  path: string,
  options: { readonly pageSize?: number; readonly maxPages?: number } = {},
): AsyncGenerator<readonly Item[]> {
  const { pageSize, maxPages = 1000 } = options;
  let cursor: string | null = null;
  let pages = 0;

  do {
    if (pages >= maxPages) {
      throw new TransportError(
        `pagination of ${path} exceeded ${maxPages} pages; the server may be ` +
          "returning a cursor that does not advance",
      );
    }
    const query: Record<string, string | number | undefined> = {};
    if (cursor !== null) query["cursor"] = cursor;
    if (pageSize !== undefined) query["page_size"] = pageSize;

    const page = await request<Collection<Item>>(path, { query });
    pages += 1;
    yield page.items;
    cursor = page.next_cursor;
  } while (cursor !== null);
}

/** Collect every page into one array. For small collections only. */
export async function fetchAll<Item>(
  path: string,
  options: { readonly pageSize?: number } = {},
): Promise<Item[]> {
  const collected: Item[] = [];
  for await (const page of walkPages<Item>(path, options)) {
    collected.push(...page);
  }
  return collected;
}
