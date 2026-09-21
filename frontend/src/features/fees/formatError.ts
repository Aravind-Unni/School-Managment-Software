/** Map fee API failures to message keys for i18n. */

import { ApiError, TransportError } from "@shared/api/errors";

/**
 * Pick a translation key for a failed fee request.
 *
 * Does not handle success paths or field-level validation display.
 */
export function feeErrorMessageKey(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 403 || error.code === "object_inaccessible") {
      return "fees.denied";
    }
    return error.messageKey;
  }
  if (error instanceof TransportError) {
    return "error.transport";
  }
  return "error.transport";
}
