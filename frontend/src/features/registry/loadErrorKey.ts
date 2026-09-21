/**
 * Map a failed registry fetch to a message key for display.
 *
 * Does not handle success paths or non-error values; callers use this only in catch
 * blocks.
 */

import { ApiError, TransportError } from "@shared/api/errors";

/** Return a shared message key suitable for useLanguage().t(). */
export function loadErrorKey(error: unknown): string {
  if (error instanceof ApiError) return error.messageKey;
  if (error instanceof TransportError) return "error.transport";
  return "error.transport";
}
