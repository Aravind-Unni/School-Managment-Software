/** Receipt print view. */

import { useEffect, useState } from "react";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { fetchPayment } from "./api";
import { feesMessages } from "./locales/messages";

export function FeeReceiptPage({ paymentId }: { paymentId?: string }) {
  const { language } = useLanguage();
  const t = feesMessages[language];
  const id =
    paymentId ??
    (typeof window !== "undefined"
      ? window.location.pathname.split("/").pop()
      : undefined);
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    fetchPayment(id)
      .then(setData)
      .catch((err: Error) =>
        setError(
          err.message.includes("404") || err.message.includes("403")
            ? t["fees.denied"]
            : err.message,
        ),
      );
  }, [id, t]);

  return (
    <main>
      <h1>{t["fees.receipt_title"]}</h1>
      {error && <p role="alert">{error}</p>}
      {data && (
        <article>
          <p>#{String(data.number)}</p>
          <p>
            {t["fees.amount"]}: {String(data.amount_paise)}
          </p>
          <p>
            {t["fees.method"]}: {String(data.method)}
          </p>
        </article>
      )}
    </main>
  );
}
