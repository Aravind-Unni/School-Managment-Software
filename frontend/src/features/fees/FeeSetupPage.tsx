/** Fee plan setup — create via POST; no list endpoint in contract. */

import { useState } from "react";
import { ApiError, TransportError } from "@shared/api/errors";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { createFeePlan, type FeePlanDTO } from "./api";
import { feesMessages } from "./locales/messages";

function toMessageKey(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 403) return "fees.denied";
    return error.messageKey;
  }
  if (error instanceof TransportError) return "error.transport";
  return "error.transport";
}

export function FeeSetupPage() {
  const { language, t } = useLanguage();
  const labels = feesMessages[language];
  const [headCode, setHeadCode] = useState("tuition");
  const [headLabelKey, setHeadLabelKey] = useState("fees.head.tuition");
  const [amountPaise, setAmountPaise] = useState("400000");
  const [dueDate, setDueDate] = useState("2026-07-01");
  const [planVersion, setPlanVersion] = useState("1");
  const [saving, setSaving] = useState(false);
  const [plan, setPlan] = useState<FeePlanDTO | null>(null);
  const [errorKey, setErrorKey] = useState<string | null>(null);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    setErrorKey(null);
    try {
      const created = await createFeePlan({
        fee_heads: [{ code: headCode, label_key: headLabelKey }],
        applicability: {},
        schedule: [
          {
            fee_head_code: headCode,
            amount_paise: Number(amountPaise),
            due_date: dueDate,
          },
        ],
        version: Number(planVersion),
      });
      setPlan(created);
    } catch (error) {
      setErrorKey(toMessageKey(error));
    } finally {
      setSaving(false);
    }
  }

  return (
    <section>
      <h1>{labels["fees.setup_title"]}</h1>
      <p>{labels["fees.setup_no_list"]}</p>
      {!plan && !errorKey && <p>{t("ui.empty")}</p>}
      <form
        onSubmit={(event) => {
          void onSubmit(event);
        }}
      >
        <label>
          {labels["fees.head_code"]}
          <input value={headCode} onChange={(e) => setHeadCode(e.target.value)} required />
        </label>
        <label>
          {labels["fees.head_label_key"]}
          <input
            value={headLabelKey}
            onChange={(e) => setHeadLabelKey(e.target.value)}
            required
          />
        </label>
        <label>
          {labels["fees.amount"]}
          <input
            type="number"
            value={amountPaise}
            onChange={(e) => setAmountPaise(e.target.value)}
            required
          />
        </label>
        <label>
          {labels["fees.due_date"]}
          <input
            type="date"
            value={dueDate}
            onChange={(e) => setDueDate(e.target.value)}
            required
          />
        </label>
        <label>
          {labels["fees.plan_version"]}
          <input
            type="number"
            min={1}
            value={planVersion}
            onChange={(e) => setPlanVersion(e.target.value)}
            required
          />
        </label>
        <button type="submit" disabled={saving}>
          {saving ? labels["fees.pending_save"] : labels["fees.submit_plan"]}
        </button>
      </form>
      {errorKey && <p role="alert">{t(errorKey)}</p>}
      {plan && (
        <section>
          <p role="status">
            {labels["fees.saved"]}: {plan.id} (v{plan.version})
          </p>
          <table>
            <caption>{labels["fees.setup_heads"]}</caption>
            <thead>
              <tr>
                <th scope="col">{labels["fees.head_code"]}</th>
                <th scope="col">{labels["fees.amount"]}</th>
                <th scope="col">{labels["fees.due_date"]}</th>
              </tr>
            </thead>
            <tbody>
              {plan.fee_heads.map((head) => {
                const row = plan.schedule.find((item) => item.fee_head_id === head.id);
                return (
                  <tr key={head.id}>
                    <th scope="row">{head.code}</th>
                    <td>{row?.amount_paise ?? "—"}</td>
                    <td>{row?.due_date ?? "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      )}
    </section>
  );
}
