/** Teacher compare / confirm / reprocess for answer-sheet candidates. */

import { useLanguage } from "@shared/i18n/LanguageContext";

export function FileReviewPage() {
  const { t } = useLanguage();
  return (
    <main>
      <h1>{t("files.review_title")}</h1>
      <p>{t("files.review_help")}</p>
      <ol>
        <li>{t("files.review_step_status")}</li>
        <li>{t("files.review_step_confirm")}</li>
        <li>{t("files.review_step_reprocess")}</li>
      </ol>
    </main>
  );
}
