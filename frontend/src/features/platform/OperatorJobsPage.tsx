/**
 * Background work the system did recently (report cards, progress checks,
 * uploaded files ...), newest first, with anything that failed at the top of
 * mind: a failed job can be retried with one tap.
 *
 * Does not handle: cancelling a running job, or jobs older than the newest
 * hundred.
 */

import { useCallback, useEffect, useState } from "react";
import { request } from "@shared/api/client";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { Problem } from "@shared/ui/Problem";
import { retryJob, type Job } from "./api";

/** "platform.modules.exchange.tasks.process_report_card" -> "process_report_card". */
function taskName(kind: string): string {
  return kind.split(".").pop() ?? kind;
}

function when(iso: string, language: string): string {
  return new Date(iso).toLocaleString(language === "ml" ? "ml-IN" : "en-IN", {
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function OperatorJobsPage() {
  const { t, language } = useLanguage();
  const [jobs, setJobs] = useState<readonly Job[] | null>(null);
  const [failedOnly, setFailedOnly] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const page = await request<{ items: Job[] }>("/api/v1/jobs", { query: { failed: failedOnly ? "true" : undefined } });
      setJobs(page.items);
    } catch (caught) {
      setError(caught);
      setJobs([]);
    }
  }, [failedOnly]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loads this screen's data
    void load();
  }, [load]);

  const retry = async (job: Job) => {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await retryJob(job.id, t("platform.retry_reason"));
      setNotice(t("platform.retry_queued"));
      await load();
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  };

  const label = (job: Job) => {
    const key = `jobs.kind.${taskName(job.kind)}`;
    const named = t(key);
    return named === key ? taskName(job.kind).replace(/_/g, " ") : named;
  };

  return (
    <section aria-labelledby="jobs-title">
      <h2 id="jobs-title">{t("platform.jobs_title")}</h2>
      <p className="hint">{t("jobs.intro")}</p>
      <div className="toolbar">
        <div className="segmented" role="group">
          <button type="button" className="seg" aria-pressed={!failedOnly} onClick={() => setFailedOnly(false)}>
            {t("jobs.all")}
          </button>
          <button type="button" className="seg" aria-pressed={failedOnly} onClick={() => setFailedOnly(true)}>
            {t("jobs.failed_only")}
          </button>
        </div>
        <button type="button" className="secondary" onClick={() => void load()}>
          {t("jobs.refresh")}
        </button>
      </div>
      {notice ? (
        <p role="status" className="notice-success">
          {notice}
        </p>
      ) : null}
      <Problem error={error} />
      {jobs === null ? (
        <p role="status">{t("ui.loading")}</p>
      ) : jobs.length === 0 ? (
        <p className="empty-state">{failedOnly ? t("jobs.none_failed") : t("jobs.none")}</p>
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th scope="col">{t("jobs.what")}</th>
                <th scope="col">{t("jobs.when")}</th>
                <th scope="col">{t("jobs.state")}</th>
                <th scope="col" />
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => {
                const failed = job.state === "failed" || job.state === "dead";
                return (
                  <tr key={job.id}>
                    <td>{label(job)}</td>
                    <td>{when(job.created_at, language)}</td>
                    <td className={failed ? "attention" : undefined}>
                      {t(`jobs.state.${job.state}`)}
                      {failed && job.error_code ? ` (${job.error_code})` : ""}
                    </td>
                    <td>
                      {failed ? (
                        <button type="button" className="secondary" disabled={busy} onClick={() => void retry(job)}>
                          {t("jobs.retry")}
                        </button>
                      ) : null}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
