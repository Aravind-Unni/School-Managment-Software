/**
 * Set a term examination: name it, tick the classes sitting it, and give each
 * subject its date and start time. One paper is created per class per subject,
 * for the classes that take that subject; the subject teachers then enter the
 * marks as usual.
 *
 * Safe to repeat: papers already set are skipped, so classes can be added
 * later. Does not handle: moving a paper (set it again on the new date) or
 * seating plans.
 */

import { useEffect, useState } from "react";
import { request } from "@shared/api/client";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { Loading } from "@shared/ui/Loading";
import { Problem } from "@shared/ui/Problem";
import * as registry from "@features/registry/api";
import { schoolToday, useSchoolStructure } from "@features/registry/useSchoolStructure";

interface Paper {
  readonly subject_id: string;
  readonly date: string;
  readonly time: string;
  readonly max_score: string;
}

interface Outcome {
  readonly created: number;
  readonly already_scheduled: number;
  readonly not_taught: number;
}

export function ExamSchedulePage() {
  const { t } = useLanguage();
  const { state } = useSchoolStructure();
  const structure = state.kind === "ready" ? state.structure : null;
  const [terms, setTerms] = useState<readonly registry.Term[]>([]);
  const [termId, setTermId] = useState("");
  const [title, setTitle] = useState("");
  const [sections, setSections] = useState<readonly string[]>([]);
  const [papers, setPapers] = useState<readonly Paper[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [outcome, setOutcome] = useState<Outcome | null>(null);

  useEffect(() => {
    registry.listAllTerms().then((rows) => {
      const sorted = [...rows].sort((a, b) => a.start.localeCompare(b.start));
      setTerms(sorted);
      const today = schoolToday();
      const current = sorted.find((row) => row.start <= today && today <= row.end) ?? sorted[sorted.length - 1];
      if (current) {
        setTermId(current.id);
        setTitle(`${current.name} ${t("exams.examination")}`);
      }
    }, setError);
  }, [t]);

  if (structure === null) return <Loading />;

  const addPaper = () =>
    setPapers((previous) => [
      ...previous,
      {
        subject_id: structure.subjects[0]?.id ?? "",
        date: previous[previous.length - 1]?.date ?? schoolToday(),
        time: "09:30",
        max_score: "80",
      },
    ]);

  const setPaper = (index: number, patch: Partial<Paper>) =>
    setPapers((previous) => previous.map((row, position) => (position === index ? { ...row, ...patch } : row)));

  const standards = [...new Set(structure.sections.map((row) => row.standardNumber))].sort((a, b) => a - b);
  const toggle = (ids: readonly string[], on: boolean) =>
    setSections((previous) => (on ? [...new Set([...previous, ...ids])] : previous.filter((id) => !ids.includes(id))));

  const ready = title.trim() !== "" && termId !== "" && sections.length > 0 && papers.length > 0;

  const save = async () => {
    setBusy(true);
    setError(null);
    setOutcome(null);
    try {
      setOutcome(
        await request<Outcome>("/api/v1/exam-schedules", {
          method: "POST",
          body: {
            term_id: termId,
            title: title.trim(),
            section_ids: sections,
            papers: papers.map((row) => ({
              subject_id: row.subject_id,
              date: row.date,
              time: row.time,
              max_score: Number(row.max_score) || 80,
            })),
          },
        }),
      );
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section aria-labelledby="exams-title">
      <h2 id="exams-title">{t("exams.title")}</h2>
      <p className="hint">{t("exams.intro")}</p>
      <form
        className="stack"
        onSubmit={(event) => {
          event.preventDefault();
          void save();
        }}
      >
        <div className="inline-fields">
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
          <label>
            {t("exams.name")}
            <input value={title} maxLength={120} onChange={(event) => setTitle(event.target.value)} />
          </label>
        </div>

        <fieldset>
          <legend>{t("exams.classes")}</legend>
          {standards.map((standard) => {
            const inStandard = structure.sections.filter((row) => row.standardNumber === standard);
            const ids = inStandard.map((row) => row.id);
            const all = ids.every((id) => sections.includes(id));
            return (
              <div key={standard} className="class-grid">
                {inStandard.map((row) => (
                  <label key={row.id} className="inline">
                    <input
                      type="checkbox"
                      checked={sections.includes(row.id)}
                      onChange={(event) => toggle([row.id], event.target.checked)}
                    />
                    {row.label}
                  </label>
                ))}
                {inStandard.length > 1 ? (
                  <button type="button" className="quiet" onClick={() => toggle(ids, !all)}>
                    {all ? t("feesetup.clear_std") : t("feesetup.all_std")} {standard}
                  </button>
                ) : null}
              </div>
            );
          })}
        </fieldset>

        <fieldset>
          <legend>{t("exams.papers")}</legend>
          {papers.length === 0 ? <p className="hint">{t("exams.no_papers")}</p> : null}
          {papers.map((paper, index) => (
            <div key={index} className="inline-fields paper-row">
              <label>
                {t("results.subject")}
                <select value={paper.subject_id} onChange={(event) => setPaper(index, { subject_id: event.target.value })}>
                  {structure.subjects.map((row) => (
                    <option key={row.id} value={row.id}>
                      {row.display_name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                {t("assessments.on")}
                <input type="date" value={paper.date} onChange={(event) => setPaper(index, { date: event.target.value })} />
              </label>
              <label>
                {t("assessments.at")}
                <input type="time" value={paper.time} onChange={(event) => setPaper(index, { time: event.target.value })} />
              </label>
              <label>
                {t("assessments.max_marks")}
                <input
                  inputMode="numeric"
                  value={paper.max_score}
                  onChange={(event) => setPaper(index, { max_score: event.target.value.replace(/\D/g, "") })}
                />
              </label>
              <div className="form-end">
                <button
                  type="button"
                  className="quiet"
                  onClick={() => setPapers((previous) => previous.filter((_, position) => position !== index))}
                >
                  {t("exams.remove_paper")}
                </button>
              </div>
            </div>
          ))}
          <button type="button" className="secondary" onClick={addPaper}>
            {t("exams.add_paper")}
          </button>
        </fieldset>

        <Problem error={error} />
        {outcome ? (
          <p role="status" className="notice-success">
            {outcome.created} {t("exams.created")}
            {outcome.already_scheduled ? ` · ${outcome.already_scheduled} ${t("exams.already")}` : ""}
            {outcome.not_taught ? ` · ${outcome.not_taught} ${t("exams.not_taught")}` : ""}
          </p>
        ) : null}
        <button type="submit" disabled={busy || !ready}>
          {busy ? t("ui.loading") : `${t("exams.save")} ${papers.length * sections.length}`}
        </button>
      </form>
    </section>
  );
}

export default ExamSchedulePage;
