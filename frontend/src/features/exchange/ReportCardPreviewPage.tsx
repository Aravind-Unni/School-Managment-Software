/** Generate report cards for a publication and poll job status. */

import { useState } from "react";
import { toLoadError } from "@shared/api/errors";
import { useLanguage } from "@shared/i18n/LanguageContext";
import {
  createReportCards,
  getReportCardJob,
  type ExchangeLocale,
  type ReportCardJob,
} from "./api";

export function ReportCardPreviewPage() {
  const { t, language } = useLanguage();
  const [publicationId, setPublicationId] = useState("");
  const [studentIds, setStudentIds] = useState("");
  const [templateVersion, setTemplateVersion] = useState("");
  const [locale, setLocale] = useState<ExchangeLocale>(language === "ml" ? "ml" : "en");
  const [jobs, setJobs] = useState<readonly ReportCardJob[]>([]);
  const [pollId, setPollId] = useState("");
  const [polled, setPolled] = useState<ReportCardJob | null>(null);
  const [errorKey, setErrorKey] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function generate() {
    setBusy(true);
    setErrorKey(null);
    setJobs([]);
    setPolled(null);
    const ids = studentIds
      .split(/[\s,]+/)
      .map((id) => id.trim())
      .filter((id) => id.length > 0);
    if (ids.length === 0 || publicationId.trim().length === 0 || templateVersion.trim().length === 0) {
      setErrorKey("exchange.report_cards_form_incomplete");
      setBusy(false);
      return;
    }
    try {
      const result = await createReportCards({
        publication_id: publicationId.trim(),
        student_ids: ids,
        locale,
        template_version: templateVersion.trim(),
      });
      setJobs(result.jobs);
    } catch (error) {
      setErrorKey(toLoadError(error).messageKey);
    } finally {
      setBusy(false);
    }
  }

  async function poll() {
    const id = pollId.trim();
    if (id.length === 0) return;
    setErrorKey(null);
    try {
      setPolled(await getReportCardJob(id));
    } catch (error) {
      setErrorKey(toLoadError(error).messageKey);
    }
  }

  return (
    <section>
      <h1>{t("exchange.report_cards_title")}</h1>
      <label>
        {t("exchange.publication_id")}
        <input value={publicationId} onChange={(event) => setPublicationId(event.target.value)} />
      </label>
      <label>
        {t("exchange.student_ids")}
        <textarea value={studentIds} onChange={(event) => setStudentIds(event.target.value)} rows={3} />
      </label>
      <label>
        {t("exchange.template_version")}
        <input value={templateVersion} onChange={(event) => setTemplateVersion(event.target.value)} />
      </label>
      <label>
        {t("exchange.locale")}
        <select value={locale} onChange={(event) => setLocale(event.target.value as ExchangeLocale)}>
          <option value="en">en</option>
          <option value="ml">ml</option>
        </select>
      </label>
      <button type="button" disabled={busy} onClick={() => void generate()}>
        {t("exchange.generate_report_cards")}
      </button>
      {jobs.length > 0 && (
        <ul>
          {jobs.map((job) => (
            <li key={job.id}>
              {job.id} · {job.student_id} · {job.state}
            </li>
          ))}
        </ul>
      )}
      <fieldset>
        <legend>{t("exchange.poll_job")}</legend>
        <label>
          {t("exchange.job_id")}
          <input value={pollId} onChange={(event) => setPollId(event.target.value)} />
        </label>
        <button type="button" onClick={() => void poll()}>
          {t("exchange.refresh_status")}
        </button>
        {polled !== null && (
          <p role="status">
            {polled.id} · {polled.state}
          </p>
        )}
      </fieldset>
      {errorKey !== null && (
        <div role="alert">
          <p>{t(errorKey)}</p>
        </div>
      )}
    </section>
  );
}
