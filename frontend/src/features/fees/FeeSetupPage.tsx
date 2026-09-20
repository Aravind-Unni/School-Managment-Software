/** Fee plan setup page — staff configures heads and schedule. */

import { useLanguage } from "@shared/i18n/LanguageContext";
import { feesMessages } from "./locales/messages";

export function FeeSetupPage() {
  const { language } = useLanguage();
  const t = feesMessages[language];
  return (
    <main>
      <h1>{t["fees.setup_title"]}</h1>
      <p>
        Configure fee heads and a versioned plan via POST /api/v1/fee-plans. Baseline
        seed installs tuition, bus and opening_balance heads.
      </p>
    </main>
  );
}
