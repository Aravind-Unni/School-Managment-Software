/**
 * Shared loading / error / empty presentation for M01's screens.
 *
 * Centralised because every screen needs all three states, and a screen that
 * forgets one shows a blank page -- which is the state users report as "broken".
 */

import { ApiError, TransportError } from "@shared/api/errors";
import { useAccessMessages } from "./useMessages";

/** Map any thrown value to a renderable message key plus a request id. */
export function toMessage(error: unknown): { messageKey: string; requestId: string | null } {
  if (error instanceof ApiError) {
    return { messageKey: error.messageKey, requestId: error.requestId };
  }
  if (error instanceof TransportError) {
    return { messageKey: "error.transport", requestId: null };
  }
  return { messageKey: "error.transport", requestId: null };
}

export function Loading() {
  const t = useAccessMessages();
  return <p role="status">{t("ui.loading")}</p>;
}

export function Empty({ messageKey = "ui.empty" }: { readonly messageKey?: string }) {
  const t = useAccessMessages();
  return <p role="status">{t(messageKey)}</p>;
}

export function Failure({
  messageKey,
  requestId,
  onRetry,
}: {
  readonly messageKey: string;
  readonly requestId?: string | null;
  readonly onRetry?: () => void;
}) {
  const t = useAccessMessages();
  return (
    <div role="alert">
      <p>{t(messageKey)}</p>
      {requestId ? (
        <p>
          <code data-testid="request-id">{requestId}</code>
        </p>
      ) : null}
      {onRetry ? (
        <button type="button" onClick={onRetry}>
          {t("ui.retry")}
        </button>
      ) : null}
    </div>
  );
}
