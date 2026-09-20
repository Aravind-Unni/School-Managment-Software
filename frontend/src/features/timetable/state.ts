/**
 * Shared loading state and error mapping for M03's pages.
 *
 * One definition, because four pages showing four different shapes of "it went
 * wrong" is how a product ends up with a screen that says nothing useful.
 */

import { ApiError, TransportError } from "@shared/api/errors";

/** What a page is currently showing. */
export type LoadState<Value> =
  | { readonly status: "loading" }
  | { readonly status: "ready"; readonly value: Value }
  | {
      readonly status: "error";
      readonly messageKey: string;
      readonly requestId: string | null;
    };

/**
 * Map any thrown value to a renderable message key.
 *
 * A TransportError becomes a transport message, never a business one: telling a
 * teacher "you do not have permission" when the network dropped is worse than a
 * generic failure, because they will go and ask for a permission they already
 * have.
 */
export function toErrorState(error: unknown): {
  readonly status: "error";
  readonly messageKey: string;
  readonly requestId: string | null;
} {
  if (error instanceof ApiError) {
    return { status: "error", messageKey: error.messageKey, requestId: error.requestId };
  }
  if (error instanceof TransportError) {
    return { status: "error", messageKey: "error.transport", requestId: null };
  }
  return { status: "error", messageKey: "error.transport", requestId: null };
}

/** The school's civil date today, as an ISO string, for a default date field. */
export function todayIso(now: Date = new Date()): string {
  // Asia/Kolkata, because a schedule is read in school time. Intl is used rather
  // than an offset constant so the zone database stays the source of truth.
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Kolkata",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(now);
  return parts;
}

/** Render "HH:MM - HH:MM" for one period, in the school's wall-clock time. */
export function periodLabel(startsAtLocal: string, endsAtLocal: string): string {
  return `${startsAtLocal} – ${endsAtLocal}`;
}

/** Shorten a UUID for display. Ids are shown only where a person must copy one. */
export function shortId(value: string): string {
  return value.slice(0, 8);
}
