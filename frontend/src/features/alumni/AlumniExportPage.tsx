/** Export filters restricted to granted fields. */

import { useLanguage } from "@shared/i18n/LanguageContext";

export function AlumniExportPage() {
  const { t } = useLanguage();
  return (
    <main>
      <h1>{t("alumni.export_title")}</h1>
      <p>
        Create exports via POST /api/v1/alumni/exports. Fields must be ⊆ policy
        exportable_fields; ungranted fields return 422
        alumni.error.export_field_not_granted.
      </p>
    </main>
  );
}
