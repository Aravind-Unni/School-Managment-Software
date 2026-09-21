/** Notice composer and audience preview. */

import { useLanguage } from "@shared/i18n/LanguageContext";

export function NoticeComposerPage() {
  const { t } = useLanguage();
  return (
    <main>
      <h1>{t("communications.notices_title")}</h1>
      <p>{t("communications.notices_help")}</p>
    </main>
  );
}
