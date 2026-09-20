/**
 * Marking grid with a side-by-side answer-sheet viewer placeholder.
 */

import { Link, useParams } from "react-router-dom";
import { useLanguage } from "@shared/i18n/LanguageContext";

export function MarkingGridPage() {
  const { t } = useLanguage();
  const { assessmentId } = useParams<{ assessmentId: string }>();

  return (
    <main>
      <h1>{t("assessment.marking.title")}</h1>
      <p>
        <Link to="/assessment/setup">{t("assessment.back")}</Link>
        {assessmentId ? ` · ${assessmentId}` : null}
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
        <section aria-label={t("assessment.marking.title")}>
          <p role="status">{t("ui.loading")}</p>
        </section>
        <aside aria-label={t("assessment.marking.viewer")}>
          <h2>{t("assessment.marking.viewer")}</h2>
          <p>{t("assessment.marking.viewer_placeholder")}</p>
        </aside>
      </div>
      {assessmentId ? (
        <p>
          <Link to={`/assessment/${assessmentId}/publish`}>{t("assessment.publish.title")}</Link>
        </p>
      ) : null}
    </main>
  );
}
