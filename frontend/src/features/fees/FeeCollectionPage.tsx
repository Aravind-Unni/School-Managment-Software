/** Manual collection form with pending-save state and idempotent retry. */

import { useState } from "react";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { DEFAULT_STUDENT, postPayment, type PaymentReceiptDTO } from "./api";
import { feeErrorMessageKey } from "./formatError";
import { feesMessages } from "./locales/messages";

export function FeeCollectionPage() {
  const { language, t: translate } = useLanguage();
  const t = feesMessages[language];
  const [chargeId, setChargeId] = useState("");
  const [amount, setAmount] = useState("40000");
  const [method, setMethod] = useState("upi");
  const [saving, setSaving] = useState(false);
  const [receipt, setReceipt] = useState<PaymentReceiptDTO | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [idemKey] = useState(() => `browser-${crypto.randomUUID()}`);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const result = await postPayment({
        student_id: DEFAULT_STUDENT,
        amount_paise: Number(amount),
        method,
        allocations: [{ charge_id: chargeId, amount_paise: Number(amount) }],
        idempotencyKey: idemKey,
      });
      setReceipt(result);
    } catch (err) {
      setError(translate(feeErrorMessageKey(err)));
    } finally {
      setSaving(false);
    }
  }

  return (
    <section>
      <h1>{t["fees.collect_title"]}</h1>
      <form
        onSubmit={(event) => {
          void onSubmit(event);
        }}
      >
        <label>
          Charge id
          <input
            value={chargeId}
            onChange={(e) => setChargeId(e.target.value)}
            required
          />
        </label>
        <label>
          {t["fees.amount"]}
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            required
          />
        </label>
        <label>
          {t["fees.method"]}
          <select value={method} onChange={(e) => setMethod(e.target.value)}>
            <option value="cash">cash</option>
            <option value="bank">bank</option>
            <option value="upi">upi</option>
          </select>
        </label>
        <button type="submit" disabled={saving}>
          {saving ? t["fees.pending_save"] : t["fees.submit_payment"]}
        </button>
      </form>
      {error && <p role="alert">{error}</p>}
      {receipt && (
        <p role="status">
          {t["fees.saved"]}: {receipt.payment.number} · outstanding{" "}
          {receipt.balance.outstanding_paise}
        </p>
      )}
    </section>
  );
}
