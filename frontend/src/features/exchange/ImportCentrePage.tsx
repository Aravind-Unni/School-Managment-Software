/** Upload, validate and commit a bulk import file. */

import { useLanguage } from "@shared/i18n/LanguageContext";

export function ImportCentrePage() {
  const { t } = useLanguage();
  return (
    <main>
      <h1>{t("exchange.imports_title")}</h1>
      <p>{t("exchange.imports_help")}</p>
      <ol>
        <li>{t("exchange.imports_step_template")}</li>
        <li>{t("exchange.imports_step_validate")}</li>
        <li>{t("exchange.imports_step_errors")}</li>
        <li>{t("exchange.imports_step_commit")}</li>
      </ol>
      <p>{t("exchange.imports_digest_note")}</p>
    </main>
  );
}
