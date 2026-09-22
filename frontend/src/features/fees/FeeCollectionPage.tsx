/**
 * Take a fee payment at the counter: find the student, tick what they are
 * paying (full balance pre-filled, editable in rupees), choose how they paid,
 * record it, print the receipt.
 *
 * The Idempotency-Key is fixed per attempt, so a double click or a retry
 * after a network drop records one payment, not two.
 * Does not handle: refunds or reversals (Fees > corrections).
 */

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { getStudent } from "@features/registry/api";
import { request } from "@shared/api/client";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { paiseFromRupees, rupees, shortDate } from "@shared/format";
import { Problem } from "@shared/ui/Problem";
import { StudentPicker, type PickedStudent } from "@features/registry/StudentPicker";
import { postPayment, type PaymentReceiptDTO } from "./api";
import { Loading } from "@shared/ui/Loading";

interface ChargeEntry {
  readonly entry_type: string;
  readonly id: string;
  readonly amount_paise: number;
  readonly balance_paise?: number;
  readonly due_date?: string;
  readonly description_key: string;
}

interface Statement {
  readonly entries: readonly ChargeEntry[];
  readonly balance: { readonly outstanding_paise: number; readonly overdue_paise: number };
}

const METHODS = ["cash", "upi", "bank"] as const;

export function FeeCollectionPage() {
  const { t, language } = useLanguage();
  const [student, setStudent] = useState<PickedStudent | null>(null);
  const [statement, setStatement] = useState<Statement | null>(null);
  const [amounts, setAmounts] = useState<Record<string, string>>({});
  const [method, setMethod] = useState<(typeof METHODS)[number]>("cash");
  const [reference, setReference] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [receipt, setReceipt] = useState<PaymentReceiptDTO | null>(null);
  const [attemptKey, setAttemptKey] = useState(() => crypto.randomUUID());
  const [params] = useSearchParams();
  const preselect = params.get("student");

  // Arriving from the overdue list opens straight on that student.
  useEffect(() => {
    if (!preselect) return;
    getStudent(preselect).then(
      (row) => setStudent({ id: row.id, display_name: row.display_name, admission_no: row.admission_no }),
      () => undefined,
    );
  }, [preselect]);

  useEffect(() => {
    if (student === null) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loads this screen's data
    setStatement(null);
    setError(null);
    request<Statement>(`/api/v1/fees/students/${student.id}/fee-statement`).then(
      (loaded) => {
        setStatement(loaded);
        const open: Record<string, string> = {};
        for (const row of loaded.entries) {
          if (row.entry_type === "charge" && (row.balance_paise ?? 0) > 0) {
            open[row.id] = String((row.balance_paise ?? 0) / 100);
          }
        }
        setAmounts(open);
      },
      setError,
    );
  }, [student]);

  const openCharges = useMemo(
    () =>
      (statement?.entries ?? [])
        .filter((row) => row.entry_type === "charge" && (row.balance_paise ?? 0) > 0)
        .sort((a, b) => (a.due_date ?? "").localeCompare(b.due_date ?? "")),
    [statement],
  );
  const allocations = openCharges
    .map((row) => ({ charge_id: row.id, amount_paise: paiseFromRupees(amounts[row.id] ?? "") ?? 0 }))
    .filter((row) => row.amount_paise > 0);
  const total = allocations.reduce((sum, row) => sum + row.amount_paise, 0);
  const tooMuch = openCharges.some(
    (row) => (paiseFromRupees(amounts[row.id] ?? "") ?? 0) > (row.balance_paise ?? 0),
  );

  const record = async () => {
    if (student === null) return;
    setBusy(true);
    setError(null);
    try {
      const trimmed = reference.trim();
      const done = await postPayment({
        student_id: student.id,
        amount_paise: total,
        method,
        ...(trimmed ? { reference: trimmed } : {}),
        allocations,
        idempotencyKey: attemptKey,
      });
      setReceipt(done);
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  };

  const startOver = () => {
    setStudent(null);
    setStatement(null);
    setReceipt(null);
    setReference("");
    setAttemptKey(crypto.randomUUID());
  };

  if (receipt !== null && student !== null) {
    return (
      <section aria-labelledby="receipt-title">
        <div className="receipt">
          <h2 id="receipt-title">{t("fees.collect.receipt_title")}</h2>
          <dl>
            <dt>{t("fees.collect.receipt_number")}</dt>
            <dd>{receipt.payment.number}</dd>
            <dt>{t("fees.collect.student")}</dt>
            <dd>
              {student.display_name} ({student.admission_no})
            </dd>
            <dt>{t("fees.collect.paid")}</dt>
            <dd>
              <strong>{rupees(receipt.payment.amount_paise)}</strong> ·{" "}
              {t(`fees.method.${receipt.payment.method}`)}
            </dd>
            <dt>{t("fees.collect.still_due")}</dt>
            <dd>{rupees(receipt.balance.outstanding_paise)}</dd>
            <dt>{t("fees.collect.date")}</dt>
            <dd>{shortDate(new Date().toISOString(), language)}</dd>
          </dl>
        </div>
        <div className="row-actions">
          <button type="button" className="secondary" onClick={() => window.print()}>
            {t("fees.collect.print")}
          </button>
          <button type="button" onClick={startOver}>
            {t("fees.collect.next")}
          </button>
        </div>
      </section>
    );
  }

  return (
    <section aria-labelledby="collect-title">
      <h2 id="collect-title">{t("fees.collect.title")}</h2>
      {student === null ? (
        <StudentPicker onPick={setStudent} />
      ) : (
        <>
          <div className="picked-person">
            <strong>{student.display_name}</strong>
            <span className="hint">{student.admission_no}</span>
            <button type="button" className="quiet" onClick={startOver}>
              {t("fees.collect.change_student")}
            </button>
          </div>
          <Problem error={error} />
          {statement === null && error === null ? <Loading /> : null}
          {statement !== null && openCharges.length === 0 ? (
            <p role="status" className="notice-success">
              {t("fees.collect.nothing_due")}
            </p>
          ) : null}
          {openCharges.length > 0 ? (
            <>
              <ul className="charge-list">
                {openCharges.map((row) => (
                  <li key={row.id}>
                    <div>
                      <strong>{t(row.description_key)}</strong>
                      <span className="hint">
                        {t("fees.collect.due")} {shortDate(row.due_date, language)} ·{" "}
                        {t("fees.collect.balance")} {rupees(row.balance_paise)}
                      </span>
                    </div>
                    <label className="amount-field">
                      <span className="visually-hidden">{t("fees.collect.amount")}</span>
                      <span aria-hidden="true">₹</span>
                      <input
                        inputMode="decimal"
                        value={amounts[row.id] ?? ""}
                        onChange={(event) =>
                          setAmounts((previous) => ({ ...previous, [row.id]: event.target.value }))
                        }
                      />
                    </label>
                  </li>
                ))}
              </ul>
              <fieldset>
                <legend>{t("fees.collect.how_paid")}</legend>
                <div className="segmented wide" role="group">
                  {METHODS.map((value) => (
                    <button
                      key={value}
                      type="button"
                      className="seg"
                      aria-pressed={method === value}
                      onClick={() => setMethod(value)}
                    >
                      {t(`fees.method.${value}`)}
                    </button>
                  ))}
                </div>
                {method !== "cash" ? (
                  <label>
                    {t("fees.collect.reference")}
                    <input value={reference} onChange={(event) => setReference(event.target.value)} />
                  </label>
                ) : null}
              </fieldset>
              {tooMuch ? <p role="alert">{t("fees.collect.too_much")}</p> : null}
              <div className="sticky-actions">
                <button
                  type="button"
                  disabled={busy || total === 0 || tooMuch}
                  onClick={() => void record()}
                >
                  {t("fees.collect.record")} {rupees(total)}
                </button>
              </div>
            </>
          ) : null}
        </>
      )}
    </section>
  );
}
