/**
 * Grant a concession: find the pupil, tap the fee to reduce, enter how much
 * (or waive the whole balance), choose why, and save.
 *
 * A concession of half the balance or more needs a recent authenticator code;
 * the server asks for it and the screen explains. Does not handle: refunds of
 * money already paid (use a refund) or standing discounts for future fees.
 */

import { useCallback, useEffect, useState } from "react";
import { request } from "@shared/api/client";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { paiseFromRupees, rupees, shortDate } from "@shared/format";
import { Problem } from "@shared/ui/Problem";
import { StudentPicker, type PickedStudent } from "@features/registry/StudentPicker";
import { postConcession } from "./api";

interface ChargeEntry {
  readonly entry_type: string;
  readonly id: string;
  readonly amount_paise: number;
  readonly balance_paise?: number;
  readonly due_date?: string;
  readonly description_key: string;
}

const REASONS = ["sibling", "staff_child", "hardship", "scholarship", "other"] as const;

export function FeeConcessionPage() {
  const { t, language } = useLanguage();
  const [student, setStudent] = useState<PickedStudent | null>(null);
  const [charges, setCharges] = useState<readonly ChargeEntry[] | null>(null);
  const [charge, setCharge] = useState<ChargeEntry | null>(null);
  const [amount, setAmount] = useState("");
  const [reason, setReason] = useState<(typeof REASONS)[number] | "">("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [done, setDone] = useState<string | null>(null);

  const loadCharges = useCallback(async (picked: PickedStudent) => {
    const statement = await request<{ entries: ChargeEntry[] }>(`/api/v1/fees/students/${picked.id}/fee-statement`);
    setCharges(statement.entries.filter((row) => row.entry_type === "charge" && (row.balance_paise ?? 0) > 0));
  }, []);

  useEffect(() => {
    if (student === null) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loads this screen's data
    setCharges(null);
    loadCharges(student).catch(setError);
  }, [student, loadCharges]);

  const balance = charge?.balance_paise ?? 0;
  const paise = paiseFromRupees(amount);
  const tooMuch = paise !== null && paise > balance;
  const why = reason === "other" ? note.trim() : [reason ? t(`concession.reason.${reason}`) : "", note.trim()].filter(Boolean).join(" – ");
  const ready = charge !== null && paise !== null && paise > 0 && !tooMuch && reason !== "" && why !== "";
  const major = paise !== null && paise * 2 >= balance;

  const save = async () => {
    if (!ready || charge === null || paise === null || student === null) return;
    setBusy(true);
    setError(null);
    setDone(null);
    try {
      await postConcession({
        charge_id: charge.id,
        amount_paise: paise,
        reason: why,
        source_key: `concession:${charge.id}:${crypto.randomUUID()}`,
        major,
      });
      setDone(`${rupees(paise)} ${t("concession.done")} ${t(charge.description_key)}.`);
      setCharge(null);
      setAmount("");
      setReason("");
      setNote("");
      await loadCharges(student);
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section aria-labelledby="concession-title">
      <h2 id="concession-title">{t("concession.title")}</h2>
      <p className="hint">{t("concession.intro")}</p>
      {student === null ? (
        <StudentPicker onPick={setStudent} />
      ) : (
        <>
          <div className="picked-person">
            <strong>{student.display_name}</strong>
            <span className="hint">{student.admission_no}</span>
            <button
              type="button"
              className="quiet"
              onClick={() => {
                setStudent(null);
                setCharge(null);
                setDone(null);
              }}
            >
              {t("fees.collect.change_student")}
            </button>
          </div>
          {done ? (
            <p role="status" className="notice-success">
              {done}
            </p>
          ) : null}
          <Problem error={error} />
          <h3>{t("concession.which_fee")}</h3>
          {charges === null ? (
            <p role="status">{t("ui.loading")}</p>
          ) : charges.length === 0 ? (
            <p className="empty-state">{t("concession.nothing_owed")}</p>
          ) : (
            <div className="teacher-choices" role="radiogroup" aria-label={t("concession.which_fee")}>
              {charges.map((row) => (
                <label key={row.id} className="teacher-choice">
                  <input
                    type="radio"
                    name="charge"
                    checked={charge?.id === row.id}
                    onChange={() => {
                      setCharge(row);
                      setAmount("");
                    }}
                  />
                  <span>
                    <strong>{t(row.description_key)}</strong>
                    <span className="hint">
                      {t("concession.owed")} {rupees(row.balance_paise ?? 0)} · {t("feesetup.due")}{" "}
                      {shortDate(row.due_date, language)}
                    </span>
                  </span>
                </label>
              ))}
            </div>
          )}

          {charge ? (
            <form
              className="stack"
              onSubmit={(event) => {
                event.preventDefault();
                void save();
              }}
            >
              <div className="inline-fields">
                <label>
                  {t("concession.amount")}
                  <input
                    inputMode="decimal"
                    value={amount}
                    aria-invalid={tooMuch || undefined}
                    onChange={(event) => setAmount(event.target.value)}
                  />
                  {tooMuch ? <span className="field-problem">{t("concession.too_much")}</span> : null}
                </label>
                <div className="form-end">
                  <button type="button" className="secondary" onClick={() => setAmount(String(balance / 100))}>
                    {t("concession.waive_all")} ({rupees(balance)})
                  </button>
                </div>
              </div>
              <fieldset>
                <legend>{t("concession.reason")}</legend>
                <div className="segmented" role="group">
                  {REASONS.map((value) => (
                    <button
                      key={value}
                      type="button"
                      className="seg"
                      aria-pressed={reason === value}
                      onClick={() => setReason(value)}
                    >
                      {t(`concession.reason.${value}`)}
                    </button>
                  ))}
                </div>
                <label>
                  {reason === "other" ? t("concession.say_why") : t("concession.note")}
                  <input value={note} maxLength={200} onChange={(event) => setNote(event.target.value)} />
                </label>
              </fieldset>
              {major && paise ? <p className="hint">{t("concession.major")}</p> : null}
              <button type="submit" disabled={busy || !ready}>
                {busy ? t("ui.loading") : paise ? `${t("concession.save")} ${rupees(paise)}` : t("concession.save")}
              </button>
            </form>
          ) : null}
        </>
      )}
    </section>
  );
}
