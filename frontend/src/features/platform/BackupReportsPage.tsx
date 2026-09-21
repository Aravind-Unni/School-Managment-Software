/** Backup and restore rehearsal reports for company ops. */

import { useLanguage } from "@shared/i18n/LanguageContext";

export function BackupReportsPage() {
  const { t } = useLanguage();
  return (
    <main>
      <h1>{t("platform.backups_title")}</h1>
      <p>{t("platform.backups_help")}</p>
      <p>{t("platform.backups_empty")}</p>
    </main>
  );
}
