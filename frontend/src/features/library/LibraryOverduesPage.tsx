/** Overdue queue for librarians. */

import { useLanguage } from "@shared/i18n/LanguageContext";

export function LibraryOverduesPage() {
  const { t } = useLanguage();
  return (
    <main>
      <h1>{t("library.overdues_title")}</h1>
      <p>
        Overdue open loans via GET /api/v1/library/overdues?as_of=YYYY-MM-DD
        (Asia/Kolkata civil date). due_date &lt; as_of is overdue.
      </p>
    </main>
  );
}
