/** Teacher compare / confirm / reprocess for answer-sheet candidates. */

import { useState } from "react";
import { toLoadError } from "@shared/api/errors";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { confirmFileQuality, getFileStatus, reprocessFile, type FileRecord } from "./api";

export function FileReviewPage() {
  const { t } = useLanguage();
  const [fileId, setFileId] = useState("");
  const [file, setFile] = useState<FileRecord | null>(null);
  const [candidateVersion, setCandidateVersion] = useState("");
  const [reprocessReason, setReprocessReason] = useState("");
  const [errorKey, setErrorKey] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function loadStatus() {
    const id = fileId.trim();
    if (id.length === 0) return;
    setLoading(true);
    setErrorKey(null);
    setNotice(null);
    try {
      setFile(await getFileStatus(id));
    } catch (error) {
      setFile(null);
      setErrorKey(toLoadError(error).messageKey);
    } finally {
      setLoading(false);
    }
  }

  async function confirm() {
    if (file === null) return;
    setNotice(null);
    try {
      const version = Number(candidateVersion);
      setFile(await confirmFileQuality(file.id, version));
      setNotice(t("files.confirmed_ok"));
    } catch (error) {
      setNotice(toLoadError(error).messageKey);
    }
  }

  async function reprocess() {
    if (file === null) return;
    setNotice(null);
    try {
      setFile(await reprocessFile(file.id, reprocessReason.trim() || t("files.reprocess_default_reason")));
      setNotice(t("files.reprocess_ok"));
    } catch (error) {
      setNotice(toLoadError(error).messageKey);
    }
  }

  return (
    <main>
      <h1>{t("files.review_title")}</h1>
      <label>
        {t("files.file_id")}
        <input value={fileId} onChange={(event) => setFileId(event.target.value)} />
      </label>
      <button type="button" disabled={loading || fileId.trim().length === 0} onClick={() => void loadStatus()}>
        {loading ? t("ui.loading") : t("files.load_status")}
      </button>
      {errorKey !== null && (
        <div role="alert">
          <p>{t(errorKey)}</p>
          <button type="button" onClick={() => void loadStatus()}>
            {t("ui.retry")}
          </button>
        </div>
      )}
      {file === null && errorKey === null && !loading && (
        <p role="status">{t("files.enter_file_id")}</p>
      )}
      {file !== null && (
        <section>
          <dl>
            <div>
              <dt>{t("files.field_state")}</dt>
              <dd>{file.state}</dd>
            </div>
            <div>
              <dt>{t("files.field_review_confirmed")}</dt>
              <dd>{file.review_confirmed ? t("files.yes") : t("files.no")}</dd>
            </div>
            {file.canonical_version !== null && (
              <div>
                <dt>{t("files.field_canonical_version")}</dt>
                <dd>{file.canonical_version}</dd>
              </div>
            )}
          </dl>
          <fieldset>
            <legend>{t("files.confirm_quality")}</legend>
            <label>
              {t("files.candidate_version")}
              <input
                type="number"
                min={1}
                value={candidateVersion}
                onChange={(event) => setCandidateVersion(event.target.value)}
              />
            </label>
            <button type="button" onClick={() => void confirm()}>
              {t("files.confirm_button")}
            </button>
          </fieldset>
          <fieldset>
            <legend>{t("files.reprocess")}</legend>
            <label>
              {t("files.reprocess_reason")}
              <input value={reprocessReason} onChange={(event) => setReprocessReason(event.target.value)} />
            </label>
            <button type="button" onClick={() => void reprocess()}>
              {t("files.reprocess_button")}
            </button>
          </fieldset>
        </section>
      )}
      {notice !== null && (
        <p role="status">{notice.startsWith("files.") || notice.startsWith("error.") ? t(notice) : notice}</p>
      )}
    </main>
  );
}
