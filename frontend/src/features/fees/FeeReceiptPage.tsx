/** Receipt print view. */

import { useEffect, useState } from "react";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { fetchPayment, type PaymentDTO } from "./api";
import { feeErrorMessageKey } from "./formatError";
import { feesMessages } from "./locales/messages";

export function FeeReceiptPage({ paymentId }: { paymentId?: string }) {
  const { language, t: translate } = useLanguage();
  const t = feesMessages[language];
  const id =
    paymentId ??
    (typeof window !== "undefined"
      ? window.location.pathname.split("/").pop()
      : undefined);
  const [data, setData] = useState<PaymentDTO | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    fetchPayment(id)
      .then(setData)
      .catch((err: unknown) => setError(translate(feeErrorMessageKey(err))));
  }, [id, t, translate]);

  return (
    <section>
      <h1>{t["fees.receipt_title"]}</h1>
      {error && <p role="alert">{error}</p>}
      {data && (
        <article>
          <p>#{data.number}</p>
          <p>
            {t["fees.amount"]}: {data.amount_paise}
          </p>
          <p>
            {t["fees.method"]}: {data.method}
          </p>
        </article>
      )}
    </section>
  );
}
