/** Overdue balances list. */

import { useEffect, useState } from "react";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { fetchOverdue } from "./api";
import { feesMessages } from "./locales/messages";

export function FeeOverduePage() {
  const { language } = useLanguage();
  const t = feesMessages[language];
  const [items, setItems] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchOverdue()
      .then((body) => setItems(body.items))
      .catch((err: Error) =>
        setError(
          err.message.includes("403") || err.message.includes("404")
            ? t["fees.denied"]
            : err.message,
        ),
      )
      .finally(() => setLoading(false));
  }, [t]);

  return (
    <main>
      <h1>{t["fees.overdue_title"]}</h1>
      {loading && <p role="status">{t["fees.loading"]}</p>}
      {error && <p role="alert">{error}</p>}
      {!loading && !error && items.length === 0 && <p>{t["fees.empty"]}</p>}
      <ul>
        {items.map((row) => (
          <li key={String(row.charge_id)}>
            {String(row.display_name ?? row.student_id)} — {String(row.balance_paise)}
          </li>
        ))}
      </ul>
    </main>
  );
}
