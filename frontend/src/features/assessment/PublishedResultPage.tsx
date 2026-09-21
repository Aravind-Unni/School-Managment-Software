/**
 * Student/guardian published result view.
 */

import { useParams } from "react-router-dom";
import { useLanguage } from "@shared/i18n/LanguageContext";

export function PublishedResultPage() {
  const { t } = useLanguage();
  const { resultId } = useParams<{ resultId: string }>();

  return (
    <section>
      <h1>{t("assessment.published.title")}</h1>
      <p>{t("assessment.grade_pending")}</p>
      {resultId ? <p data-testid="result-id">{resultId}</p> : null}
    </section>
  );
}
