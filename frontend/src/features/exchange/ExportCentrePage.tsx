/**
 * Download a class list or report as a spreadsheet or PDF: choose what,
 * for which class (and term, where marks are involved), tick the columns,
 * and the file is prepared and offered for download.
 *
 * Only columns the school may share are offered; private notes never appear.
 * Does not handle: whole-school exports in one file (one class at a time).
 */

import { useEffect, useState } from "react";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { Problem } from "@shared/ui/Problem";
import * as registry from "@features/registry/api";
import { schoolToday, useSchoolStructure } from "@features/registry/useSchoolStructure";
import { createExport, downloadExport, getExport, type ExchangeLocale, type ExportDataset, type ExportJob } from "./api";

interface DatasetSpec {
  readonly id: ExportDataset;
  readonly needsTerm: boolean;
  /** Columns offered, in order; the first ones are ticked by default. */
  readonly fields: readonly string[];
  readonly ticked: readonly string[];
}

const DATASETS: readonly DatasetSpec[] = [
  { id: "class_roster", needsTerm: false, fields: ["display_name", "student_id", "enrolment_id"], ticked: ["display_name"] },
  {
    id: "attendance_summary",
    needsTerm: false,
    fields: ["display_name", "percentage", "present", "absent", "marked", "eligible", "unmarked", "student_id"],
    ticked: ["display_name", "percentage", "present", "absent", "marked"],
  },
  {
    id: "progress",
    needsTerm: true,
    fields: ["display_name", "mean_marks", "result_count", "metric", "source", "student_id"],
    ticked: ["display_name", "mean_marks", "result_count"],
  },
  {
    id: "subject_summary",
    needsTerm: true,
    fields: ["display_name", "subject_id", "marks_obtained", "student_id", "result_revision_id"],
    ticked: ["display_name", "subject_id", "marks_obtained"],
  },
  {
    id: "at_risk",
    needsTerm: true,
    fields: ["display_name", "risk_status", "absent_periods", "unmarked_periods", "published_results", "student_id", "threshold_policy_version"],
    ticked: ["display_name", "risk_status", "absent_periods", "published_results"],
  },
  {
    id: "ptm_summary",
    needsTerm: false,
    fields: ["display_name", "outstanding_paise", "overdue_paise", "attendance_marked", "student_id"],
    ticked: ["display_name", "outstanding_paise", "overdue_paise", "attendance_marked"],
  },
];

export function ExportCentrePage() {
  const { t, language } = useLanguage();
  const { state } = useSchoolStructure();
  const sections = state.kind === "ready" ? state.structure.sections : [];
  const [terms, setTerms] = useState<readonly registry.Term[]>([]);
  const [dataset, setDataset] = useState<DatasetSpec>(DATASETS[0] as DatasetSpec);
  const [sectionId, setSectionId] = useState("");
  const [termId, setTermId] = useState("");
  const [fields, setFields] = useState<readonly string[]>(DATASETS[0]?.ticked ?? []);
  const [format, setFormat] = useState<"csv" | "pdf">("csv");
  const [locale, setLocale] = useState<ExchangeLocale>(language === "ml" ? "ml" : "en");
  const [job, setJob] = useState<ExportJob | null>(null);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    registry.listAllTerms().then((rows) => {
      setTerms(rows);
      const today = schoolToday();
      const current = rows.find((row) => row.start <= today && today <= row.end) ?? rows[0];
      if (current) setTermId(current.id);
    }, setError);
  }, []);

  // Poll a queued export every two seconds until it is ready.
  useEffect(() => {
    if (job === null || job.state === "ready" || job.state === "failed") return undefined;
    const timer = window.setInterval(() => {
      getExport(job.id).then(async (status) => {
        setJob(status);
        if (status.state === "ready") setDownloadUrl((await downloadExport(status.id)).authorized_read_url);
      }, setError);
    }, 2000);
    return () => window.clearInterval(timer);
  }, [job]);

  const choose = (spec: DatasetSpec) => {
    setDataset(spec);
    setFields(spec.ticked);
    setJob(null);
    setDownloadUrl(null);
  };

  const chosenSection = sectionId || sections[0]?.id || "";
  const ready = chosenSection !== "" && fields.length > 0 && (!dataset.needsTerm || termId !== "");

  const start = async () => {
    setBusy(true);
    setError(null);
    setJob(null);
    setDownloadUrl(null);
    try {
      const filters: Record<string, string> = { section_id: chosenSection };
      if (dataset.needsTerm) filters.publication_id = termId;
      const ordered = dataset.fields.filter((field) => fields.includes(field));
      setJob(await createExport({ dataset: dataset.id, filters, fields: ordered, format, locale }));
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section aria-labelledby="exports-title">
      <h2 id="exports-title">{t("exchange.exports_title")}</h2>
      <p className="hint">{t("exports.intro")}</p>

      <h3>{t("exports.what")}</h3>
      <div className="teacher-choices" role="radiogroup">
        {DATASETS.map((spec) => (
          <label key={spec.id} className="teacher-choice">
            <input type="radio" name="dataset" checked={dataset.id === spec.id} onChange={() => choose(spec)} />
            <span>
              <strong>{t(`exports.dataset.${spec.id}`)}</strong>
              <span className="hint">{t(`exports.dataset.${spec.id}.about`)}</span>
            </span>
          </label>
        ))}
      </div>

      <div className="inline-fields">
        <label>
          {t("cards.class")}
          <select value={chosenSection} onChange={(event) => setSectionId(event.target.value)}>
            {sections.map((row) => (
              <option key={row.id} value={row.id}>
                {row.label}
              </option>
            ))}
          </select>
        </label>
        {dataset.needsTerm ? (
          <label>
            {t("cards.term")}
            <select value={termId} onChange={(event) => setTermId(event.target.value)}>
              {terms.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        <label>
          {t("exports.format")}
          <select value={format} onChange={(event) => setFormat(event.target.value as "csv" | "pdf")}>
            <option value="csv">{t("exports.format.csv")}</option>
            <option value="pdf">PDF</option>
          </select>
        </label>
        <label>
          {t("exports.language")}
          <select value={locale} onChange={(event) => setLocale(event.target.value as ExchangeLocale)}>
            <option value="en">English</option>
            <option value="ml">മലയാളം</option>
          </select>
        </label>
      </div>

      <fieldset>
        <legend>{t("exports.columns")}</legend>
        <div className="class-grid">
          {dataset.fields.map((field) => (
            <label key={field} className="inline">
              <input
                type="checkbox"
                checked={fields.includes(field)}
                onChange={(event) =>
                  setFields((previous) =>
                    event.target.checked ? [...previous, field] : previous.filter((item) => item !== field),
                  )
                }
              />
              {t(`exports.field.${field}`)}
            </label>
          ))}
        </div>
      </fieldset>

      <Problem error={error} />
      <div className="row-actions">
        <button aria-busy={busy} type="button" disabled={busy || !ready} onClick={() => void start()}>
          {busy ? t("ui.loading") : t("exchange.create_export")}
        </button>
        {job && !downloadUrl && job.state !== "failed" ? <span role="status">{t("exports.preparing")}</span> : null}
        {job?.state === "failed" ? <span className="attention">{t("exports.failed")}</span> : null}
        {downloadUrl ? (
          <a className="button-link" href={downloadUrl} target="_blank" rel="noreferrer">
            {t("exports.download")}
          </a>
        ) : null}
      </div>
    </section>
  );
}
