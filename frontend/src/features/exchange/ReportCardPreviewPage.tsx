/** Generate report cards for a publication and preview what each binds. */

import { useLanguage } from "@shared/i18n/LanguageContext";

export function ReportCardPreviewPage() {
  const { t } = useLanguage();
  return (
    <main>
      <h1>{t("exchange.report_cards_title")}</h1>
      <p>{t("exchange.report_cards_help")}</p>
      <ol>
        <li>{t("exchange.report_cards_step_select")}</li>
        <li>{t("exchange.report_cards_step_generate")}</li>
        <li>{t("exchange.report_cards_step_poll")}</li>
      </ol>
      <p>{t("exchange.report_cards_font_pending")}</p>
    </main>
  );
}
