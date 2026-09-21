/** Operator safe retry queue for platform jobs. */

import { useState } from "react";
import { toLoadError } from "@shared/api/errors";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { getJob, retryJob, type Job } from "./api";

export function OperatorJobsPage() {
  const { t } = useLanguage();
  const [jobId, setJobId] = useState("");
  const [job, setJob] = useState<Job | null>(null);
  const [errorKey, setErrorKey] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    const id = jobId.trim();
    if (id.length === 0) return;
    setLoading(true);
    setErrorKey(null);
    setNotice(null);
    try {
      setJob(await getJob(id));
    } catch (error) {
      setJob(null);
      setErrorKey(toLoadError(error).messageKey);
    } finally {
      setLoading(false);
    }
  }

  async function retry() {
    if (job === null) return;
    setNotice(null);
    setErrorKey(null);
    try {
      setJob(await retryJob(job.id, t("platform.retry_reason")));
      setNotice(t("platform.retry_queued"));
    } catch (error) {
      setErrorKey(toLoadError(error).messageKey);
    }
  }

  return (
    <section>
      <h1>{t("platform.jobs_title")}</h1>
      <label>
        {t("platform.job_id")}
        <input value={jobId} onChange={(event) => setJobId(event.target.value)} />
      </label>
      <button type="button" disabled={loading || jobId.trim().length === 0} onClick={() => void load()}>
        {loading ? t("ui.loading") : t("platform.load_job")}
      </button>
      {errorKey !== null && (
        <div role="alert">
          <p>{t(errorKey)}</p>
          <button type="button" onClick={() => void load()}>
            {t("ui.retry")}
          </button>
        </div>
      )}
      {job === null && errorKey === null && !loading && (
        <p role="status">{t("platform.jobs_lookup_hint")}</p>
      )}
      {job !== null && (
        <section>
          <dl>
            <div>
              <dt>{t("platform.job_kind")}</dt>
              <dd>{job.kind}</dd>
            </div>
            <div>
              <dt>{t("platform.job_state")}</dt>
              <dd>{job.state}</dd>
            </div>
            <div>
              <dt>{t("platform.job_progress")}</dt>
              <dd>{job.progress}%</dd>
            </div>
            {job.error_code !== null && (
              <div>
                <dt>{t("platform.job_error")}</dt>
                <dd>{job.error_code}</dd>
              </div>
            )}
          </dl>
          {(job.state === "failed" || job.state === "dead") && (
            <button type="button" onClick={() => void retry()}>
              {t("platform.retry_job")}
            </button>
          )}
        </section>
      )}
      {notice !== null && <p role="status">{t(notice)}</p>}
    </section>
  );
}
