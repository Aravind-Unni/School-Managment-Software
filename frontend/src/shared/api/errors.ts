/**
 * The frozen error envelope, as the browser sees it.
 *
 * Mirrors contracts/common/error-envelope.schema.json. Every non-2xx response
 * from every module has this shape, so error handling is written once here
 * rather than per feature.
 */

/** Stable machine-readable error codes. Must match the backend ErrorCode enum. */
export const ERROR_CODES = [
  "unauthenticated",
  "stale_auth",
  "action_denied",
  "object_inaccessible",
  "version_conflict",
  "state_conflict",
  "validation_failed",
] as const;

export type ErrorCode = (typeof ERROR_CODES)[number];

/** One field-scoped validation problem. */
export interface FieldError {
  readonly field: string;
  readonly message_key: string;
}

/** The complete error body. `field_errors` is always present, possibly empty. */
export interface ErrorEnvelope {
  readonly code: ErrorCode;
  readonly message_key: string;
  readonly request_id: string;
  readonly field_errors: readonly FieldError[];
}

/**
 * An API call that failed with a well-formed envelope.
 *
 * Carries the HTTP status alongside the envelope so a caller can branch on
 * either. Prefer branching on `code`: the status is derived from it, and two
 * codes share 401 and 409.
 */
export class ApiError extends Error {
  readonly status: number;
  readonly envelope: ErrorEnvelope;

  constructor(status: number, envelope: ErrorEnvelope) {
    super(`${envelope.code}: ${envelope.message_key}`);
    this.name = "ApiError";
    this.status = status;
    this.envelope = envelope;
  }

  get code(): ErrorCode {
    return this.envelope.code;
  }

  get messageKey(): string {
    return this.envelope.message_key;
  }

  get requestId(): string {
    return this.envelope.request_id;
  }

  get fieldErrors(): readonly FieldError[] {
    return this.envelope.field_errors;
  }

  /** True when the remedy is to re-assert two-factor authentication. */
  get needsFreshTwoFactor(): boolean {
    return this.envelope.code === "stale_auth";
  }

  /** Field path -> message keys, for rendering beside form inputs. */
  fieldErrorsByField(): Record<string, string[]> {
    const grouped: Record<string, string[]> = {};
    for (const problem of this.envelope.field_errors) {
      (grouped[problem.field] ??= []).push(problem.message_key);
    }
    return grouped;
  }
}

/**
 * A failure that produced no usable envelope: a network drop, a proxy error
 * page, or a 500 that never reached the shared handler.
 *
 * Kept distinct from ApiError so the UI does not claim a business reason for a
 * transport failure.
 */
export class TransportError extends Error {
  readonly status: number | null;

  constructor(message: string, status: number | null = null) {
    super(message);
    this.name = "TransportError";
    this.status = status;
  }
}

/**
 * Narrow an unknown parsed body to an ErrorEnvelope.
 *
 * Deliberately strict: a body missing any contracted key is NOT an envelope, and
 * treating it as one would let a proxy's HTML error page surface as a business
 * error.
 */
export function isErrorEnvelope(value: unknown): value is ErrorEnvelope {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate["code"] === "string" &&
    (ERROR_CODES as readonly string[]).includes(candidate["code"]) &&
    typeof candidate["message_key"] === "string" &&
    typeof candidate["request_id"] === "string" &&
    Array.isArray(candidate["field_errors"])
  );
}
