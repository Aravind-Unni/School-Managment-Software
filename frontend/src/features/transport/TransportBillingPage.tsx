/** Period billing runs and reconciliation. */

import { useLanguage } from "@shared/i18n/LanguageContext";

export function TransportBillingPage() {
  const { t } = useLanguage();
  return (
    <main>
      <h1>{t("transport.billing_title")}</h1>
      <p>
        Queue a period billing run via POST /api/v1/bus-billing-runs. Fees charges use
        source_key transport:&#123;id&#125;:YYYY-MM:period.
      </p>
    </main>
  );
}
