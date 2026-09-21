/** Request a dataset export and fetch its short-lived download URL. */

import { useState } from "react";
import { toLoadError } from "@shared/api/errors";
import { useLanguage } from "@shared/i18n/LanguageContext";
import {
  createExport,
  downloadExport,
  getExport,
  type ExchangeLocale,
  type ExportDataset,
  type ExportJob,
} from "./api";

const DATASETS: readonly ExportDataset[] = [
  "attendance_summary",
  "progress",
  "at_risk",
  "ptm_summary",
  "class_roster",
  "subject_summary",
];

export function ExportCentrePage() {
  const { t, language } = useLanguage();
  const [dataset, setDataset] = useState<ExportDataset>("class_roster");
  const [format, setFormat] = useState<"csv" | "xlsx" | "pdf">("csv");
  const [locale, setLocale] = useState<ExchangeLocale>(language === "ml" ? "ml" : "en");
  const [fields, setFields] = useState("");
  const [filtersJson, setFiltersJson] = useState("{}");
  const [job, setJob] = useState<ExportJob | null>(null);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [errorKey, setErrorKey] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function enqueue() {
    setBusy(true);
    setErrorKey(null);
    setJob(null);
    setDownloadUrl(null);
    let filters: Record<string, unknown>;
    try {
      filters = JSON.parse(filtersJson) as Record<string, unknown>;
    } catch {
      setErrorKey("exchange.filters_invalid");
      setBusy(false);
      return;
    }
    const fieldList = fields
      .split(/[\s,]+/)
      .map((field) => field.trim())
      .filter((field) => field.length > 0);
    if (fieldList.length === 0) {
      setErrorKey("exchange.fields_required");
      setBusy(false);
      return;
    }
    try {
      setJob(await createExport({ dataset, filters, fields: fieldList, format, locale }));
    } catch (error) {
      setErrorKey(toLoadError(error).messageKey);
    } finally {
      setBusy(false);
    }
  }

  async function poll() {
    if (job === null) return;
    setErrorKey(null);
    try {
      const status = await getExport(job.id);
      setJob(status);
      if (status.state === "ready") {
        const access = await downloadExport(status.id);
        setDownloadUrl(access.authorized_read_url);
      }
    } catch (error) {
      setErrorKey(toLoadError(error).messageKey);
    }
  }

  return (
    <section>
      <h1>{t("exchange.exports_title")}</h1>
      <label>
        {t("exchange.dataset")}
        <select value={dataset} onChange={(event) => setDataset(event.target.value as ExportDataset)}>
          {DATASETS.map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
      </label>
      <label>
        {t("exchange.format")}
        <select value={format} onChange={(event) => setFormat(event.target.value as "csv" | "xlsx" | "pdf")}>
          <option value="csv">csv</option>
          <option value="xlsx">xlsx</option>
          <option value="pdf">pdf</option>
        </select>
      </label>
      <label>
        {t("exchange.locale")}
        <select value={locale} onChange={(event) => setLocale(event.target.value as ExchangeLocale)}>
          <option value="en">en</option>
          <option value="ml">ml</option>
        </select>
      </label>
      <label>
        {t("exchange.fields_csv")}
        <input value={fields} onChange={(event) => setFields(event.target.value)} />
      </label>
      <label>
        {t("exchange.filters_json")}
        <textarea value={filtersJson} onChange={(event) => setFiltersJson(event.target.value)} rows={3} />
      </label>
      <button type="button" disabled={busy} onClick={() => void enqueue()}>
        {t("exchange.create_export")}
      </button>
      {job !== null && (
        <section>
          <p role="status">
            {job.id} · {job.state}
          </p>
          <button type="button" onClick={() => void poll()}>
            {t("exchange.refresh_status")}
          </button>
          {downloadUrl !== null && (
            <p>
              <a href={downloadUrl} rel="noopener noreferrer">
                {t("exchange.download_link")}
              </a>
            </p>
          )}
        </section>
      )}
      {errorKey !== null && (
        <div role="alert">
          <p>{t(errorKey)}</p>
        </div>
      )}
    </section>
  );
}
