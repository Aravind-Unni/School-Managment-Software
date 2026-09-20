/** Contact fields and preference editor. */

import { useLanguage } from "@shared/i18n/LanguageContext";

export function AlumniProfilePage() {
  const { t } = useLanguage();
  return (
    <main>
      <h1>{t("alumni.profile_title")}</h1>
      <p>
        Patch contact via PATCH /api/v1/alumni/&#123;id&#125;/contact with expected_version.
        Preference withdrawal emits alumni.contact_preference_changed and blocks
        campaign selection.
      </p>
    </main>
  );
}
