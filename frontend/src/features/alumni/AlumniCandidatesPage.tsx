/** Pending graduate/leaver candidate review. */

import { useLanguage } from "@shared/i18n/LanguageContext";

export function AlumniCandidatesPage() {
  const { t } = useLanguage();
  return (
    <main>
      <h1>{t("alumni.candidates_title")}</h1>
      <p>
        Review pending candidates via GET /api/v1/alumni/candidates. Approve or
        exclude with POST /api/v1/alumni/candidates/&#123;id&#125;/approve. Transfer stays
        pending when transfer_include_as_alumni is unset.
      </p>
    </main>
  );
}
