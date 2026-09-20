/** Librarian issue/return desk. Barcode input is ordinary keyboard text. */

import { useLanguage } from "@shared/i18n/LanguageContext";

export function LibraryDeskPage() {
  const { t } = useLanguage();
  return (
    <main>
      <h1>{t("library.desk_title")}</h1>
      <p>
        Issue via POST /api/v1/library/loans with Idempotency-Key. Return via
        POST /api/v1/library/loans/&#123;id&#125;/return. Scan accession numbers with a
        keyboard wedge; no hardware integration.
      </p>
    </main>
  );
}
