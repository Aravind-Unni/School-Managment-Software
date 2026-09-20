/** Concession confirmation with reason. */

import { useState } from "react";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { feesMessages } from "./locales/messages";

export function FeeConcessionPage() {
  const { language } = useLanguage();
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
      const res = await fetch("/api/v1/concessions", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          charge_id: chargeId,
          amount_paise: Number(amount),
          reason,
          source_key: `concession:ui:${chargeId}:${amount}`,
          major: Number(amount) >= 50000,
        }),
      });
      if (!res.ok) throw new Error(`concession_failed_${res.status}`);
      setStatus(t["fees.saved"]);
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "failed");
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
