/** Delivery status dashboard and retry controls. */

import { useLanguage } from "@shared/i18n/LanguageContext";

export function DeliveryDashboardPage() {
  const { t } = useLanguage();
  return (
    <main>
      <h1>{t("communications.deliveries_title")}</h1>
      <p>{t("communications.deliveries_help")}</p>
    </main>
  );
}
