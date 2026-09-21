/** Map performance API failures to a user-visible message. */

import { ApiError } from "@shared/api/errors";

export function performanceErrorMessage(error: unknown, deniedLabel: string): string {
  if (error instanceof ApiError) {
    if (error.status === 403 || error.status === 404) return deniedLabel;
    return error.messageKey;
  }
  if (error instanceof Error) return error.message;
  return deniedLabel;
}
