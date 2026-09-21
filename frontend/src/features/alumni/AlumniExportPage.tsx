/** Export filters restricted to granted fields. */

import { useState } from "react";
import { toLoadError } from "@shared/api/errors";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { createAlumniExport, type ExportField, type ExportJob, type LeavingOutcome } from "./api";

const FIELD_OPTIONS: readonly ExportField[] = [
  "display_name",
  "admission_no",
  "leaving_year",
  "outcome",
  "email",
  "phone",
  "postal_address",
];

export function AlumniExportPage() {
  const { t } = useLanguage();
  const [year, setYear] = useState("");
  const [outcome, setOutcome] = useState<"" | LeavingOutcome>("");
  const [fields, setFields] = useState<readonly ExportField[]>(["display_name", "admission_no"]);
  const [job, setJob] = useState<ExportJob | null>(null);
  const [errorKey, setErrorKey] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function toggleField(field: ExportField) {
    setFields((current) =>
      current.includes(field) ? current.filter((item) => item !== field) : [...current, field],
    );
  }

  async function submit() {
    setSubmitting(true);
    setErrorKey(null);
    setJob(null);
    try {
      const accepted = await createAlumniExport({
        filters: {
          year: year.length > 0 ? Number(year) : null,
          outcome: outcome !== "" ? outcome : null,
        },
        fields,
      });
      setJob(accepted);
    } catch (error) {
      setErrorKey(toLoadError(error).messageKey);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section>
      <h1>{t("alumni.export_title")}</h1>
      <fieldset>
        <legend>{t("alumni.export_filters")}</legend>
        <label>
          {t("alumni.filter_year")}
          <input type="number" value={year} onChange={(event) => setYear(event.target.value)} />
        </label>
        <label>
          {t("alumni.filter_outcome")}
          <select
            value={outcome}
            onChange={(event) => setOutcome(event.target.value as "" | LeavingOutcome)}
          >
            <option value="">{t("alumni.filter_any")}</option>
            <option value="graduate">{t("alumni.outcome.graduate")}</option>
            <option value="transfer">{t("alumni.outcome.transfer")}</option>
          </select>
        </label>
      </fieldset>
      <fieldset>
        <legend>{t("alumni.export_fields")}</legend>
        {FIELD_OPTIONS.map((field) => (
          <label key={field}>
            <input
              type="checkbox"
              checked={fields.includes(field)}
              onChange={() => toggleField(field)}
            />
            {field}
          </label>
        ))}
      </fieldset>
      <button type="button" disabled={submitting || fields.length === 0} onClick={() => void submit()}>
        {submitting ? t("ui.loading") : t("alumni.start_export")}
      </button>
      {errorKey !== null && (
        <div role="alert">
          <p>{t(errorKey)}</p>
        </div>
      )}
      {job !== null && (
        <p role="status">
          {t("alumni.export_queued")}: {job.job_id} · {job.state}
        </p>
      )}
    </section>
  );
}
