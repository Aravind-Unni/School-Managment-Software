/** Period billing reconciliation and run queue. */

import { useCallback, useEffect, useState } from "react";
import { ApiError, TransportError } from "@shared/api/errors";
import { useLanguage } from "@shared/i18n/LanguageContext";
import {
  createBillingRun,
  getBillingReconciliation,
  type BillingRunDTO,
  type ReconciliationDTO,
} from "./api";

type LoadState =
  | { readonly status: "loading" }
  | { readonly status: "ready"; readonly data: ReconciliationDTO }
  | { readonly status: "error"; readonly messageKey: string };

function defaultPeriod(): string {
  return "2026-06";
}

function toMessageKey(error: unknown): string {
  if (error instanceof ApiError) return error.messageKey;
  if (error instanceof TransportError) return "error.transport";
  return "error.transport";
}

export function TransportBillingPage() {
  const { t } = useLanguage();
  const [period, setPeriod] = useState(defaultPeriod);
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [runResult, setRunResult] = useState<BillingRunDTO | null>(null);
  const [runErrorKey, setRunErrorKey] = useState<string | null>(null);
  const [queuing, setQueuing] = useState(false);

  const load = useCallback(async (value: string) => {
    setState({ status: "loading" });
    setRunResult(null);
    setRunErrorKey(null);
    try {
      const data = await getBillingReconciliation(value);
      setState({ status: "ready", data });
    } catch (error) {
      setState({ status: "error", messageKey: toMessageKey(error) });
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loads this screen's data
    void load(period);
  }, [period, load]);

  async function onQueueRun() {
    setQueuing(true);
    setRunErrorKey(null);
    setRunResult(null);
    try {
      const run = await createBillingRun({ period, policy_version: 1 });
      setRunResult(run);
      await load(period);
    } catch (error) {
      setRunErrorKey(toMessageKey(error));
    } finally {
      setQueuing(false);
    }
  }

  return (
    <section>
      <h1>{t("transport.billing_title")}</h1>
      <label>
        {t("transport.billing_period")}
        <input
          type="month"
          value={period}
          onChange={(event) => setPeriod(event.target.value)}
          aria-label={t("transport.billing_period")}
        />
      </label>
      {state.status === "loading" && <p role="status">{t("ui.loading")}</p>}
      {state.status === "error" && (
        <p role="alert">
          {t(state.messageKey)}
          <button type="button" onClick={() => void load(period)}>
            {t("ui.retry")}
          </button>
        </p>
      )}
      {state.status === "ready" && (
        <>
          {state.data.items.length === 0 ? (
            <p>{t("ui.empty")}</p>
          ) : (
            <table>
              <caption>{t("transport.reconciliation_title")}</caption>
              <thead>
                <tr>
                  <th scope="col">{t("transport.col_kind")}</th>
                  <th scope="col">{t("transport.col_owner")}</th>
                  <th scope="col">{t("transport.col_state")}</th>
                  <th scope="col">{t("transport.col_error")}</th>
                </tr>
              </thead>
              <tbody>
                {state.data.items.map((item, index) => (
                  <tr key={`${item.kind}-${item.source_key ?? index}`}>
                    <th scope="row">{item.kind}</th>
                    <td>{item.owner}</td>
                    <td>{item.state ?? "—"}</td>
                    <td>{item.error_code ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <button type="button" disabled={queuing} onClick={() => void onQueueRun()}>
            {queuing ? t("transport.queuing") : t("transport.queue_run")}
          </button>
        </>
      )}
      {runErrorKey && <p role="alert">{t(runErrorKey)}</p>}
      {runResult && (
        <p role="status">
          {t("transport.run_queued")}: {runResult.job_id} · {runResult.state} ·{" "}
          {t("transport.preview_eligible")} {runResult.preview.eligible_count}
        </p>
      )}
    </section>
  );
}
