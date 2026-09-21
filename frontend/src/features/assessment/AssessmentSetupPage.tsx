/**
 * Create a draft assessment (setup).
 */

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  listAcademicYears,
  listSections,
  listSubjects,
  listTerms,
} from "@features/registry/api";
import { fetchAll } from "@shared/api/client";
import { ApiError, TransportError } from "@shared/api/errors";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { createAssessment } from "./api";
import { rememberAssessment } from "./storage";

function toMessageKey(error: unknown): string {
  if (error instanceof ApiError) return error.messageKey;
  if (error instanceof TransportError) return "error.transport";
  return "error.transport";
}

export function AssessmentSetupPage() {
  const { t } = useLanguage();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [loadingRefs, setLoadingRefs] = useState(true);
  const [errorKey, setErrorKey] = useState<string | null>(null);
  const [yearId, setYearId] = useState("");
  const [termId, setTermId] = useState("");
  const [sectionId, setSectionId] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [years, setYears] = useState<{ id: string; name: string }[]>([]);
  const [terms, setTerms] = useState<{ id: string; name: string; year_id: string }[]>([]);
  const [sections, setSections] = useState<{ id: string; name: string }[]>([]);
  const [subjects, setSubjects] = useState<{ id: string; name: string }[]>([]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [yearRows, termRows, sectionRows, subjectRows] = await Promise.all([
          fetchAll<Awaited<ReturnType<typeof listAcademicYears>>["items"][number]>(
            "/api/v1/academic-years",
          ),
          fetchAll<Awaited<ReturnType<typeof listTerms>>["items"][number]>("/api/v1/terms"),
          fetchAll<Awaited<ReturnType<typeof listSections>>["items"][number]>(
            "/api/v1/sections",
          ),
          fetchAll<Awaited<ReturnType<typeof listSubjects>>["items"][number]>(
            "/api/v1/subjects",
          ),
        ]);
        if (cancelled) return;
        setYears(yearRows.map((row) => ({ id: row.id, name: row.name })));
        setTerms(termRows.map((row) => ({ id: row.id, name: row.name, year_id: row.year_id })));
        setSections(sectionRows.map((row) => ({ id: row.id, name: row.name })));
        setSubjects(subjectRows.map((row) => ({ id: row.id, name: row.display_name })));
        if (yearRows[0]) setYearId(yearRows[0].id);
        if (termRows[0]) setTermId(termRows[0].id);
        if (sectionRows[0]) setSectionId(sectionRows[0].id);
        if (subjectRows[0]) setSubjectId(subjectRows[0].id);
        setErrorKey(null);
      } catch (error) {
        if (!cancelled) setErrorKey(toMessageKey(error));
      } finally {
        if (!cancelled) setLoadingRefs(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const termsForYear = terms.filter((row) => row.year_id === yearId || yearId === "");

  async function onCreate() {
    if (!yearId || !termId || !sectionId || !subjectId) return;
    setBusy(true);
    setErrorKey(null);
    try {
      const created = await createAssessment({
        year_id: yearId,
        term_id: termId,
        section_id: sectionId,
        subject_id: subjectId,
        type: "written_test",
        policy_version: "illustrative-v0",
        components: [{ max_score: "100.00", weight: "1.000", topic: null, question_type: null }],
      });
      rememberAssessment(created);
      void navigate(`/assessment/${created.id}/marking`, { state: { assessment: created } });
    } catch (error) {
      setErrorKey(toMessageKey(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      <h1>{t("assessment.setup.title")}</h1>
      {loadingRefs && <p role="status">{t("ui.loading")}</p>}
      {errorKey && <p role="alert">{t(errorKey)}</p>}
      {!loadingRefs && (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void onCreate();
          }}
        >
          <label>
            {t("assessment.setup.year")}
            <select value={yearId} onChange={(event) => setYearId(event.target.value)} required>
              {years.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t("assessment.setup.term")}
            <select value={termId} onChange={(event) => setTermId(event.target.value)} required>
              {termsForYear.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t("assessment.setup.section")}
            <select value={sectionId} onChange={(event) => setSectionId(event.target.value)} required>
              {sections.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t("assessment.setup.subject")}
            <select value={subjectId} onChange={(event) => setSubjectId(event.target.value)} required>
              {subjects.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name}
                </option>
              ))}
            </select>
          </label>
          <button type="submit" disabled={busy}>
            {t("assessment.setup.submit")}
          </button>
        </form>
      )}
    </section>
  );
}
