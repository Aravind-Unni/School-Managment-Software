/**
 * Render a failed request: the message, each field problem, and the request id
 * a school office can quote to support.
 *
 * Accepts anything thrown. Does not handle: success notices (callers own those).
 */

import { ApiError, TransportError } from "@shared/api/errors";
import { useLanguage } from "@shared/i18n/LanguageContext";

/** Human label for a backend field path, e.g. "profile.date_of_birth". */
function fieldLabel(field: string): string {
  const last = field.split(".").pop() ?? field;
  return last.replace(/\[\d+\]/g, "").replace(/_/g, " ");
}

export function Problem({ error }: { readonly error: unknown }) {
  const { t } = useLanguage();
  if (error === null || error === undefined) return null;
  if (error instanceof ApiError) {
    return (
      <div role="alert" className="problem">
        <p>{t(error.messageKey)}</p>
        {error.fieldErrors.length > 0 ? (
          <ul>
            {error.fieldErrors.map((problem) => (
              <li key={`${problem.field}:${problem.message_key}`}>
                <strong>{fieldLabel(problem.field)}</strong>: {t(problem.message_key)}
              </li>
            ))}
          </ul>
        ) : null}
        <p className="request-id">
          <small>
            {t("ui.request_id")}: <code>{error.requestId}</code>
          </small>
        </p>
      </div>
    );
  }
  if (error instanceof TransportError) {
    return (
      <p role="alert" className="problem">
        {t("error.transport")}
      </p>
    );
  }
  return (
    <p role="alert" className="problem">
      {t("error.transport")}
    </p>
  );
}
