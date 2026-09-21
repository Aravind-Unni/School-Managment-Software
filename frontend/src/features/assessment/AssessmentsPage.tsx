/**
 * Assessments: my tests with how far marking has got and the next step for
 * each, and a short form to set a new one.
 *
 * Teachers choose from the classes and subjects they teach; the principal
 * and academic office see every class. Draft -> marks entered -> submitted
 * -> approved -> published is shown as plain words, never as codes.
 */

import { useCallback, useEffect, useMemo, useState, type CSSProperties } from "react";
import { Link, useNavigate } from "react-router-dom";
import { request } from "@shared/api/client";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { shortDate } from "@shared/format";
import { Problem } from "@shared/ui/Problem";
import { useSession } from "@app/SessionContext";
import * as registry from "@features/registry/api";
import { schoolToday, useSchoolStructure } from "@features/registry/useSchoolStructure";
import { subjectColour } from "@features/timetable/subjectColours";
import { createAssessment } from "./api";

interface Row {
  readonly id: string;
  readonly section_label: string | null;
  readonly subject_name: string | null;
  readonly type: string;
  readonly max_score: string;
  readonly state: string;
  readonly pupils: number;
  readonly marked: number;
  readonly created_at: string;
}

const TYPES = ["written_test", "assignment", "practical", "project"] as const;

export function AssessmentsPage() {
  const { t, language } = useLanguage();
  const navigate = useNavigate();
  const { session } = useSession();
  const { state } = useSchoolStructure();
  const [rows, setRows] = useState<readonly Row[] | null>(null);
  const [assignments, setAssignments] = useState<readonly registry.TeachingAssignment[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [pair, setPair] = useState("");
  const [type, setType] = useState<(typeof TYPES)[number]>("written_test");
  const [maxScore, setMaxScore] = useState("50");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const page = await request<{ items: Row[] }>("/api/v1/assessments");
      setRows(page.items);
    } catch (caught) {
      setError(caught);
      setRows([]);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loads this screen's data
    void load();
    registry.listAllTeachingAssignments().then(setAssignments, () => setAssignments([]));
  }, [load]);

  const structure = state.kind === "ready" ? state.structure : null;
  const today = schoolToday();
  const options = useMemo(() => {
    if (!structure) return [];
    const label = new Map(structure.sections.map((row) => [row.id, row.label]));
    const subject = new Map(structure.subjects.map((row) => [row.id, row.display_name]));
    const mine = assignments.filter(
      (row) =>
        row.staff_id === session?.actor_id &&
        row.from_date <= today &&
        (!row.to_date || row.to_date >= today),
    );
    const source =
      mine.length > 0
        ? mine
        : assignments.filter((row) => row.from_date <= today && (!row.to_date || row.to_date >= today));
    const unique = new Map<string, string>();
    for (const row of source) {
      if (!label.has(row.section_id)) continue;
      unique.set(
        `${row.section_id}|${row.subject_id}`,
        `${label.get(row.section_id)} · ${subject.get(row.subject_id) ?? ""}`,
      );
    }
    return [...unique.entries()].sort((a, b) => a[1].localeCompare(b[1]));
  }, [structure, assignments, session?.actor_id, today]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loads this screen's data
    if (pair === "" && options[0]) setPair(options[0][0]);
  }, [options, pair]);

  const create = async () => {
    const [sectionId, subjectId] = pair.split("|");
    if (!structure?.year || !sectionId || !subjectId) return;
    setBusy(true);
    setError(null);
    try {
      const terms = await registry.listAllTerms();
      const term =
        terms.find((row) => row.year_id === structure.year?.id && row.start <= today && today <= row.end) ??
        terms.find((row) => row.year_id === structure.year?.id);
      const max = `${Number(maxScore).toFixed(2)}`;
      const created = await createAssessment({
        year_id: structure.year.id,
        term_id: term?.id,
        section_id: sectionId,
        subject_id: subjectId,
        type,
        policy_version: "school-v1",
        max_score: max,
        components: [{ max_score: max, weight: "1.000", topic: null, question_type: null }],
      });
      void navigate(`/assessment/${created.id}/marking`);
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  };

  const next = (row: Row) => {
    if (row.state === "draft" || row.state === "reopened") {
      return { to: `/assessment/${row.id}/marking`, label: t("assessments.enter_marks") };
    }
    if (row.state === "submitted" || row.state === "approved") {
      return { to: `/assessment/${row.id}/marking`, label: t("assessments.review") };
    }
    return { to: `/assessment/${row.id}/marking`, label: t("assessments.view") };
  };

  return (
    <section aria-labelledby="assessments-title">
      <h2 id="assessments-title">{t("assessments.title")}</h2>
      <Problem error={error} />
      <div className="two-column">
        <div>
          <h3>{t("assessments.mine")}</h3>
          {rows === null ? <p role="status">{t("ui.loading")}</p> : null}
          {rows !== null && rows.length === 0 ? <p className="hint">{t("assessments.none")}</p> : null}
          <ul className="period-cards">
            {(rows ?? []).map((row) => {
              const action = next(row);
              return (
                <li
                  key={row.id}
                  style={{ "--subject": subjectColour(row.subject_name ?? "") } as CSSProperties}
                  className={row.state === "published" ? "done" : ""}
                >
                  <div className="period-when">
                    <strong>{t(`assessments.type.${row.type}`)}</strong>
                    <span>{shortDate(row.created_at, language)}</span>
                  </div>
                  <div className="period-what">
                    <strong>
                      {row.section_label} · {row.subject_name}
                    </strong>
                    <span className="hint">
                      {t(`assessments.state.${row.state}`)} · {row.marked}/{row.pupils}{" "}
                      {t("assessments.marked")} · {t("assessments.out_of")} {Number(row.max_score)}
                    </span>
                  </div>
                  <Link className={row.state === "published" ? "button-link secondary" : "button-link"} to={action.to}>
                    {action.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
        {options.length > 0 ? (
          <form
            className="stack"
            onSubmit={(event) => {
              event.preventDefault();
              void create();
            }}
          >
            <h3>{t("assessments.new")}</h3>
            <label>
              {t("assessments.class_subject")}
              <select value={pair} onChange={(event) => setPair(event.target.value)}>
                {options.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              {t("assessments.kind")}
              <select value={type} onChange={(event) => setType(event.target.value as (typeof TYPES)[number])}>
                {TYPES.map((value) => (
                  <option key={value} value={value}>
                    {t(`assessments.type.${value}`)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              {t("assessments.max_marks")}
              <input
                inputMode="numeric"
                value={maxScore}
                onChange={(event) => setMaxScore(event.target.value.replace(/[^\d.]/g, ""))}
              />
            </label>
            <button type="submit" disabled={busy || !(Number(maxScore) > 0)}>
              {t("assessments.create")}
            </button>
          </form>
        ) : null}
      </div>
    </section>
  );
}

export default AssessmentsPage;
