/** Upload, validate and commit a bulk import file. */

import { useCallback, useEffect, useState } from "react";
import { toLoadError } from "@shared/api/errors";
import { useLanguage } from "@shared/i18n/LanguageContext";
import {
  commitImport,
  createImport,
  getImport,
  getImportTemplate,
  listImportErrors,
  type ImportDataset,
  type ImportJob,
  type ImportRowError,
  type ImportTemplate,
} from "./api";

const DATASETS: readonly ImportDataset[] = [
  "enrolments",
  "opening_balances",
  "results",
  "library_loans",
];

export function ImportCentrePage() {
  const { t } = useLanguage();
  const [dataset, setDataset] = useState<ImportDataset>("enrolments");
  const [template, setTemplate] = useState<ImportTemplate | null>(null);
  const [fileRef, setFileRef] = useState("");
  const [job, setJob] = useState<ImportJob | null>(null);
  const [errors, setErrors] = useState<readonly ImportRowError[]>([]);
  const [digest, setDigest] = useState("");
  const [errorKey, setErrorKey] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loadingTemplate, setLoadingTemplate] = useState(false);

  const loadTemplate = useCallback(async () => {
    setLoadingTemplate(true);
    setErrorKey(null);
    try {
      setTemplate(await getImportTemplate(dataset));
    } catch (error) {
      setTemplate(null);
      setErrorKey(toLoadError(error).messageKey);
    } finally {
      setLoadingTemplate(false);
    }
  }, [dataset]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadTemplate();
  }, [loadTemplate]);

  async function startValidation() {
    setNotice(null);
    setErrorKey(null);
    setJob(null);
    setErrors([]);
    try {
      const created = await createImport({
        dataset,
        file_ref: fileRef.trim(),
        mode: "validate",
      });
      const status = await getImport(created.job_id);
      setJob(status);
      if (status.error_count > 0) {
        const page = await listImportErrors(status.id);
        setErrors(page.items);
      }
      setNotice(t("exchange.import_started"));
    } catch (error) {
      setErrorKey(toLoadError(error).messageKey);
    }
  }

  async function refreshJob() {
    if (job === null) return;
    setErrorKey(null);
    try {
      const status = await getImport(job.id);
      setJob(status);
      if (status.error_count > 0) {
        const page = await listImportErrors(status.id);
        setErrors(page.items);
      }
    } catch (error) {
      setErrorKey(toLoadError(error).messageKey);
    }
  }

  async function commit() {
    if (job === null) return;
    setNotice(null);
    setErrorKey(null);
    try {
      const updated = await commitImport(
        job.id,
        { validation_version: job.validation_version, source_digest: digest.trim() },
        crypto.randomUUID(),
      );
      setJob(updated);
      setNotice(t("exchange.import_commit_accepted"));
    } catch (error) {
      setErrorKey(toLoadError(error).messageKey);
    }
  }

  return (
    <section>
      <h1>{t("exchange.imports_title")}</h1>
      <label>
        {t("exchange.dataset")}
        <select value={dataset} onChange={(event) => setDataset(event.target.value as ImportDataset)}>
          {DATASETS.map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
      </label>
      {loadingTemplate && <p role="status">{t("ui.loading")}</p>}
      {template !== null && (
        <section>
          <p>
            {t("exchange.template_columns")}: {template.columns.join(", ")}
          </p>
        </section>
      )}
      <label>
        {t("exchange.file_ref")}
        <input value={fileRef} onChange={(event) => setFileRef(event.target.value)} />
      </label>
      <button type="button" disabled={fileRef.trim().length === 0} onClick={() => void startValidation()}>
        {t("exchange.start_validation")}
      </button>
      {job !== null && (
        <section>
          <p role="status">
            {job.id} · {job.state} · {t("exchange.accepted")}: {job.accepted_count} ·{" "}
            {t("exchange.errors")}: {job.error_count}
          </p>
          <button type="button" onClick={() => void refreshJob()}>
            {t("exchange.refresh_status")}
          </button>
          {errors.length === 0 && job.error_count === 0 && job.state === "validated" && (
            <>
              <label>
                {t("exchange.source_digest")}
                <input value={digest} onChange={(event) => setDigest(event.target.value)} />
              </label>
              <button type="button" disabled={digest.trim().length !== 64} onClick={() => void commit()}>
                {t("exchange.commit_import")}
              </button>
            </>
          )}
          {errors.length > 0 && (
            <ul>
              {errors.map((row) => (
                <li key={`${row.row}-${row.field}-${row.code}`}>
                  {t("exchange.row")} {row.row}: {row.field} · {row.code}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
      {notice !== null && <p role="status">{t(notice)}</p>}
      {errorKey !== null && (
        <div role="alert">
          <p>{t(errorKey)}</p>
          <button type="button" onClick={() => void loadTemplate()}>
            {t("ui.retry")}
          </button>
        </div>
      )}
    </section>
  );
}
