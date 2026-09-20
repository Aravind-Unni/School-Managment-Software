/** Catalogue search and availability. */

import { useLanguage } from "@shared/i18n/LanguageContext";

export function LibraryCataloguePage() {
  const { t } = useLanguage();
  return (
    <main>
      <h1>{t("library.catalogue_title")}</h1>
      <p>
        Search titles via GET /api/v1/library/titles?q=. Availability via GET
        /api/v1/library/titles/&#123;id&#125;/availability. Baseline seed has one Malayalam
        title with accession ACC-1001.
      </p>
    </main>
  );
}
