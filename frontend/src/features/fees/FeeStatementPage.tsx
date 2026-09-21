/** Student fee statement with balance totals. */

import { useEffect, useState } from "react";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { DEFAULT_STUDENT, fetchStatement, type FeeStatementDTO } from "./api";
import { feeErrorMessageKey } from "./formatError";
import { feesMessages } from "./locales/messages";

export function FeeStatementPage() {
  const { language, t: translate } = useLanguage();
  const t = feesMessages[language];
  const [data, setData] = useState<FeeStatementDTO | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    fetchStatement(DEFAULT_STUDENT)
      .then((dto) => {
        if (!cancelled) {
          setData(dto);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(translate(feeErrorMessageKey(err)));
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [t, translate]);

  return (
    <section>
      <h1>{t["fees.statement_title"]}</h1>
      {loading && <p role="status">{t["fees.loading"]}</p>}
      {error && <p role="alert">{error}</p>}
      {!loading && !error && data && data.entries.length === 0 && (
        <p>{t["fees.empty"]}</p>
      )}
      {data && (
        <section>
          <p>
            {t["fees.outstanding"]}: {data.balance.outstanding_paise} ·{" "}
            {t["fees.overdue"]}: {data.balance.overdue_paise}
          </p>
          <table>
            <caption>{t["fees.statement_title"]}</caption>
            <thead>
              <tr>
                <th scope="col">Type</th>
                <th scope="col">{t["fees.amount"]}</th>
              </tr>
            </thead>
            <tbody>
              {data.entries.map((e) => (
                <tr key={`${e.entry_type}-${e.id}`}>
                  <th scope="row">{e.entry_type}</th>
                  <td>{e.amount_paise}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </section>
  );
}
