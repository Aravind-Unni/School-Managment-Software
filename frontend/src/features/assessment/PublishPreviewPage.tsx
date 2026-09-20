/**
 * Publish preview for an approved assessment.
 */

import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError, TransportError } from "@shared/api/errors";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { publishAssessment } from "./api";

function toMessageKey(error: unknown): string {
  if (error instanceof ApiError) return error.messageKey;
  if (error instanceof TransportError) return "error.transport";
  return "error.transport";
}

export function PublishPreviewPage() {
  const { t } = useLanguage();
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const [version, setVersion] = useState(1);
  const [message, setMessage] = useState<string | null>(null);
  const [errorKey, setErrorKey] = useState<string | null>(null);

  async function onPublish() {
    if (!assessmentId) return;
    setErrorKey(null);
    setMessage(null);
    try {
      const published = await publishAssessment(
        assessmentId,
        version,
        `publish-${assessmentId}-${version}`,
      );
      setMessage(published.publication_id);
    } catch (error) {
      setErrorKey(toMessageKey(error));
    }
  }

  return (
    <main>
      <h1>{t("assessment.publish.title")}</h1>
      <p>
        <Link to={assessmentId ? `/assessment/${assessmentId}/marking` : "/assessment/setup"}>
          {t("assessment.back")}
        </Link>
      </p>
      <label>
        expected version
        <input
          type="number"
          min={1}
          value={version}
          onChange={(event) => setVersion(Number(event.target.value))}
        />
      </label>
      {errorKey && <p role="alert">{t(errorKey)}</p>}
      {message && <p role="status">{message}</p>}
      <button type="button" onClick={() => void onPublish()}>
        {t("assessment.publish.action")}
      </button>
    </main>
  );
}
