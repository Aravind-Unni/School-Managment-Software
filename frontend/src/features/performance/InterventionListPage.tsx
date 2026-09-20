/**
 * Intervention task list for assigned staff.
 */

import { useLanguage } from "@shared/i18n/LanguageContext";
import { performanceMessages } from "./locales/messages";

export function InterventionListPage() {
  const { language } = useLanguage();
  const t = performanceMessages[language];
  return (
    <main>
      <h1>{t["performance.interventions_title"]}</h1>
      <p>{t["performance.empty"]}</p>
    </main>
  );
}
