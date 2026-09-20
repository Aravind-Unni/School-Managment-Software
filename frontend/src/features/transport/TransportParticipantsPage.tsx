/** Effective bus participants on a school date. */

import { useLanguage } from "@shared/i18n/LanguageContext";

export function TransportParticipantsPage() {
  const { t } = useLanguage();
  return (
    <main>
      <h1>{t("transport.participants_title")}</h1>
      <p>
        List effective participants via GET /api/v1/bus-participants?date=YYYY-MM-DD.
        Baseline seed opts S1 in from 2026-06-01; S2 remains out.
      </p>
    </main>
  );
}
