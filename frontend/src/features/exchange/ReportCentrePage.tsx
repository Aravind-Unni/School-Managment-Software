/** Browse immutable report snapshots and their supersession chain. */

import { useLanguage } from "@shared/i18n/LanguageContext";

export function ReportCentrePage() {
  const { t } = useLanguage();
  return (
    <main>
      <h1>{t("exchange.reports_title")}</h1>
      <p>{t("exchange.reports_help")}</p>
      <ul>
        <li>{t("exchange.reports_bound_revisions")}</li>
        <li>{t("exchange.reports_superseded")}</li>
        <li>{t("exchange.reports_download")}</li>
      </ul>
    </main>
  );
}
