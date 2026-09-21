/** Overdue balances list. */

import { useEffect, useState } from "react";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { fetchOverdue, type OverdueItemDTO } from "./api";
import { feeErrorMessageKey } from "./formatError";
import { feesMessages } from "./locales/messages";

export function FeeOverduePage() {
  const { language, t: translate } = useLanguage();
  const t = feesMessages[language];
  const [items, setItems] = useState<readonly OverdueItemDTO[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchOverdue()
      .then((body) => setItems(body.items))
      .catch((err: unknown) => setError(translate(feeErrorMessageKey(err))))
      .finally(() => setLoading(false));
  }, [t, translate]);

  return (
    <section>
      <h1>{t["fees.overdue_title"]}</h1>
      {loading && <p role="status">{t["fees.loading"]}</p>}
      {error && <p role="alert">{error}</p>}
      {!loading && !error && items.length === 0 && <p>{t["fees.empty"]}</p>}
      <ul>
        {items.map((row) => (
          <li key={row.charge_id}>
            {row.display_name ?? row.student_id} — {row.balance_paise}
          </li>
        ))}
      </ul>
    </section>
  );
}
