/**
 * Create a draft assessment (setup).
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, TransportError } from "@shared/api/errors";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { createAssessment } from "./api";

function toMessageKey(error: unknown): string {
  if (error instanceof ApiError) return error.messageKey;
  if (error instanceof TransportError) return "error.transport";
  return "error.transport";
}

/** Baseline fixture ids for the standalone demo create form. */
const DEMO = {
  year_id: "66632073-44d5-5c85-9583-95ee9424d514",
  term_id: "bb72592f-20fa-5e9c-ba91-2f81cd0f47eb",
  section_id: "86847c87-bedd-505d-9e2f-3bb35275320c",
  subject_id: "a0ba60ad-0b03-5fbc-8a07-11bb5c400ae4",
} as const;

export function AssessmentSetupPage() {
  const { t } = useLanguage();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [errorKey, setErrorKey] = useState<string | null>(null);

  async function onCreate() {
    setBusy(true);
    setErrorKey(null);
    try {
      const created = await createAssessment({
        ...DEMO,
        type: "written_test",
        policy_version: "illustrative-v0",
        components: [{ max_score: "100.00", weight: "1.000", topic: null, question_type: null }],
      });
      void navigate(`/assessment/${created.id}/marking`);
    } catch (error) {
      setErrorKey(toMessageKey(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <h1>{t("assessment.setup.title")}</h1>
      <p>{t("assessment.grade_pending")}</p>
      {errorKey && <p role="alert">{t(errorKey)}</p>}
      <button type="button" disabled={busy} onClick={() => void onCreate()}>
        {t("assessment.setup.submit")}
      </button>
    </main>
  );
}
