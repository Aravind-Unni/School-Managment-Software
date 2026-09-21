/** Filtered audit viewer — redacted diffs only for school admins. */

import { useLanguage } from "@shared/i18n/LanguageContext";

export function AuditViewerPage() {
  const { t } = useLanguage();
  return (
    <main>
      <h1>{t("platform.audit_title")}</h1>
      <p>{t("platform.audit_help")}</p>
      <p>{t("platform.audit_empty")}</p>
    </main>
  );
}
