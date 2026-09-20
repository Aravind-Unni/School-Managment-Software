/** Alumni directory search by year and outcome. */

import { useLanguage } from "@shared/i18n/LanguageContext";

export function AlumniDirectoryPage() {
  const { t } = useLanguage();
  return (
    <main>
      <h1>{t("alumni.directory_title")}</h1>
      <p>
        Search approved alumni via GET /api/v1/alumni?year=&amp;outcome=. Snapshot
        fields only — no editable grade history.
      </p>
    </main>
  );
}
