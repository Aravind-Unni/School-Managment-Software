/** Parent/student viewer — canonical bytes only via server-minted grant. */

import { useLanguage } from "@shared/i18n/LanguageContext";

export function ParentFileViewerPage() {
  const { t } = useLanguage();
  return (
    <main>
      <h1>{t("files.viewer_title")}</h1>
      <p>{t("files.viewer_help")}</p>
    </main>
  );
}
