/**
 * Bus billing for one month: one button charges every rider their bus fee
 * (part months by the school's rule), and anything that could not be charged
 * is listed by pupil with what went wrong and a Try again button.
 *
 * Charging is safe to repeat: pupils already billed for the month are skipped.
 * Does not handle: refunds or fee changes for one pupil (use Concessions).
 */

import { useCallback, useEffect, useState } from "react";
import { request } from "@shared/api/client";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { Problem } from "@shared/ui/Problem";
import { schoolToday } from "@features/registry/useSchoolStructure";
import { createBillingRun, getBillingReconciliation, type BillingRunDTO, type ReconciliationDTO } from "./api";
import { Loading } from "@shared/ui/Loading";

function monthLabel(period: string, language: string): string {
  const [year, month] = period.split("-").map(Number);
  return new Date(year ?? 2026, (month ?? 1) - 1, 1).toLocaleDateString(language === "ml" ? "ml-IN" : "en-IN", {
    month: "long",
    year: "numeric",
  });
}

export function TransportBillingPage() {
  const { t, language } = useLanguage();
  const [period, setPeriod] = useState(schoolToday().slice(0, 7));
  const [data, setData] = useState<ReconciliationDTO | null>(null);
  const [names, setNames] = useState<ReadonlyMap<string, string>>(new Map());
  const [run, setRun] = useState<BillingRunDTO | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(async (value: string) => {
    try {
      const [recon, riders] = await Promise.all([
        getBillingReconciliation(value),
        request<{ items: { participation_id: string; display_name: string }[] }>("/api/v1/bus-participants", {
          query: { date: `${value}-15` },
        }),
      ]);
      setData(recon);
      setNames(new Map(riders.items.map((row) => [row.participation_id, row.display_name])));
    } catch (caught) {
      setError(caught);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loads this screen's data
    void load(period);
  }, [period, load]);

  const act = async (work: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await work();
      await load(period);
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  };

  const billMonth = () => act(async () => setRun(await createBillingRun({ period, policy_version: 1 })));
  const retry = (billingRequestId: string) =>
    act(() => request(`/api/v1/bus-billing-requests/${billingRequestId}/retry`, { method: "POST", body: {} }));

  const problems = data?.items ?? [];

  return (
    <section aria-labelledby="bus-billing-title">
      <h2 id="bus-billing-title">{t("busbill.title")}</h2>
      <p className="hint">{t("busbill.intro")}</p>
      <div className="inline-fields">
        <label>
          {t("busbill.month")}
          <input
            type="month"
            value={period}
            onChange={(event) => {
              setPeriod(event.target.value);
              setRun(null);
            }}
          />
        </label>
        <div className="form-end">
          <button aria-busy={busy} type="button" disabled={busy} onClick={() => void billMonth()}>
            {busy ? t("ui.loading") : `${t("busbill.bill")} ${monthLabel(period, language)}`}
          </button>
        </div>
      </div>
      <Problem error={error} />
      {run ? (
        <p role="status" className="notice-success">
          {run.preview.eligible_count} {t("busbill.charged")} · {run.preview.already_billed_count}{" "}
          {t("busbill.already")}
          {run.preview.blocked_count ? ` · ${run.preview.blocked_count} ${t("busbill.blocked")}` : ""}
        </p>
      ) : null}
      <h3>{t("busbill.attention")}</h3>
      {data === null ? (
        <Loading />
      ) : problems.length === 0 ? (
        <p className="empty-state">{t("busbill.all_good")}</p>
      ) : (
        <ul className="charge-list">
          {problems.map((item, index) => (
            <li key={`${item.billing_request_id ?? item.participation_id ?? index}`}>
              <div>
                <strong>{(item.participation_id && names.get(item.participation_id)) || t("busbill.a_rider")}</strong>
                <span className="attention">{t(`busbill.kind.${item.kind}`)}</span>
                {item.error_code ? <span className="hint">{t(item.error_code)}</span> : null}
              </div>
              {item.retryable && item.billing_request_id ? (
                <button
                  type="button"
                  className="secondary"
                  disabled={busy}
                  onClick={() => void retry(item.billing_request_id as string)}
                >
                  {t("jobs.retry")}
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
