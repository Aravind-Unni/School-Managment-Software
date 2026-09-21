/** Look up immutable report snapshots by id. */

import { useState } from "react";
import { toLoadError } from "@shared/api/errors";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { downloadReport, getReportSnapshot, type ReportSnapshot } from "./api";

export function ReportCentrePage() {
  const { t } = useLanguage();
  const [reportId, setReportId] = useState("");
  const [snapshot, setSnapshot] = useState<ReportSnapshot | null>(null);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [errorKey, setErrorKey] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    const id = reportId.trim();
    if (id.length === 0) return;
    setLoading(true);
    setErrorKey(null);
    setSnapshot(null);
    setDownloadUrl(null);
    try {
      const report = await getReportSnapshot(id);
      setSnapshot(report);
    } catch (error) {
      setErrorKey(toLoadError(error).messageKey);
    } finally {
      setLoading(false);
    }
  }

  async function fetchDownload() {
    if (snapshot === null) return;
    setErrorKey(null);
    try {
      const access = await downloadReport(snapshot.id);
      setDownloadUrl(access.authorized_read_url);
    } catch (error) {
      setErrorKey(toLoadError(error).messageKey);
    }
  }

  return (
    <section>
      <h1>{t("exchange.reports_title")}</h1>
      <label>
        {t("exchange.report_id")}
        <input value={reportId} onChange={(event) => setReportId(event.target.value)} />
      </label>
      <button type="button" disabled={loading || reportId.trim().length === 0} onClick={() => void load()}>
        {loading ? t("ui.loading") : t("exchange.load_report")}
      </button>
      {errorKey !== null && (
        <div role="alert">
          <p>{t(errorKey)}</p>
          <button type="button" onClick={() => void load()}>
            {t("ui.retry")}
          </button>
        </div>
      )}
      {snapshot === null && errorKey === null && !loading && (
        <p role="status">{t("exchange.report_id_hint")}</p>
      )}
      {snapshot !== null && (
        <section>
          <dl>
            <div>
              <dt>{t("exchange.report_type")}</dt>
              <dd>{snapshot.type}</dd>
            </div>
            <div>
              <dt>{t("exchange.report_state")}</dt>
              <dd>{snapshot.state}</dd>
            </div>
            <div>
              <dt>{t("exchange.locale")}</dt>
              <dd>{snapshot.locale}</dd>
            </div>
          </dl>
          <button type="button" onClick={() => void fetchDownload()}>
            {t("exchange.fetch_download")}
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
    </section>
  );
}
