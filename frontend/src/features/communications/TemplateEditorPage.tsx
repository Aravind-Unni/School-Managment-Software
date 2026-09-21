/** Bilingual template editor. */

import { useLanguage } from "@shared/i18n/LanguageContext";

export function TemplateEditorPage() {
  const { t } = useLanguage();
  return (
    <main>
      <h1>{t("communications.templates_title")}</h1>
      <p>{t("communications.templates_help")}</p>
    </main>
  );
}
