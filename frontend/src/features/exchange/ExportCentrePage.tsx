/** Request a dataset export and fetch its short-lived download URL. */

import { useLanguage } from "@shared/i18n/LanguageContext";

export function ExportCentrePage() {
  const { t } = useLanguage();
  return (
    <main>
      <h1>{t("exchange.exports_title")}</h1>
      <p>{t("exchange.exports_help")}</p>
      <ol>
        <li>{t("exchange.exports_step_create")}</li>
        <li>{t("exchange.exports_step_poll")}</li>
        <li>{t("exchange.exports_step_download")}</li>
      </ol>
      <p>{t("exchange.exports_fields_note")}</p>
    </main>
  );
}
