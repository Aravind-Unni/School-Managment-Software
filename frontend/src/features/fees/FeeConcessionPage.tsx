/** Concession confirmation with reason. */

import { useState } from "react";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { postConcession } from "./api";
import { feeErrorMessageKey } from "./formatError";
import { feesMessages } from "./locales/messages";

export function FeeConcessionPage() {
  const { language, t: translate } = useLanguage();
  const t = feesMessages[language];
  const [chargeId, setChargeId] = useState("");
  const [amount, setAmount] = useState("10000");
  const [reason, setReason] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    setStatus(null);
    try {
      await postConcession({
        charge_id: chargeId,
        amount_paise: Number(amount),
        reason,
        source_key: `concession:ui:${chargeId}:${amount}`,
        major: Number(amount) >= 50000,
      });
      setStatus(t["fees.saved"]);
    } catch (err) {
      setStatus(translate(feeErrorMessageKey(err)));
    } finally {
      setSaving(false);
    }
  }

  return (
    <main>
      <h1>{t["fees.concession_title"]}</h1>
      <form
        onSubmit={(event) => {
          void onSubmit(event);
        }}
      >
        <label>
          Charge id
          <input value={chargeId} onChange={(e) => setChargeId(e.target.value)} required />
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
          {t["fees.reason"]}
          <input value={reason} onChange={(e) => setReason(e.target.value)} required />
        </label>
        <button type="submit" disabled={saving}>
          {saving ? t["fees.pending_save"] : t["fees.submit_concession"]}
        </button>
      </form>
      {status && <p role="status">{status}</p>}
    </main>
  );
}
