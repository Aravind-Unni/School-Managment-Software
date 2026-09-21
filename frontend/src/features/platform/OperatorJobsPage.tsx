/** Operator safe retry queue for platform jobs. */

import { useLanguage } from "@shared/i18n/LanguageContext";

export function OperatorJobsPage() {
  const { t } = useLanguage();
  return (
    <main>
      <h1>{t("platform.jobs_title")}</h1>
      <p>{t("platform.jobs_help")}</p>
      <p>{t("platform.jobs_empty")}</p>
    </main>
  );
}
