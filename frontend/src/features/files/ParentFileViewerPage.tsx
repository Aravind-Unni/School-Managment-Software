/** Parent/student viewer — metadata via status; canonical bytes use server grants only. */

import { useState } from "react";
import { toLoadError } from "@shared/api/errors";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { getFileStatus, type FileRecord } from "./api";

export function ParentFileViewerPage() {
  const { t } = useLanguage();
  const [fileId, setFileId] = useState("");
  const [file, setFile] = useState<FileRecord | null>(null);
  const [errorKey, setErrorKey] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    const id = fileId.trim();
    if (id.length === 0) return;
    setLoading(true);
    setErrorKey(null);
    setFile(null);
    try {
      setFile(await getFileStatus(id));
    } catch (error) {
      setErrorKey(toLoadError(error).messageKey);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section>
      <h1>{t("files.viewer_title")}</h1>
      <p>{t("files.viewer_api_note")}</p>
      <label>
        {t("files.file_id")}
        <input value={fileId} onChange={(event) => setFileId(event.target.value)} />
      </label>
      <button aria-busy={loading} type="button" disabled={loading || fileId.trim().length === 0} onClick={() => void load()}>
        {loading ? t("ui.loading") : t("files.load_status")}
      </button>
      {errorKey !== null && (
        <div role="alert">
          <p>{t(errorKey)}</p>
          <button type="button" onClick={() => void load()}>
            {t("ui.retry")}
          </button>
        </div>
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
          </dl>
          {!file.review_confirmed && <p role="status">{t("files.viewer_not_ready")}</p>}
        </section>
      )}
      {file === null && errorKey === null && !loading && (
        <p role="status">{t("files.enter_file_id")}</p>
      )}
    </section>
  );
}
