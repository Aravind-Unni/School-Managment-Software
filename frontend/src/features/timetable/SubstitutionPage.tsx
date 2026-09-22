/**
 * Cover a period: choose the day and class, tap the period that needs cover,
 * then tap a teacher. Teachers already teaching at that time are shown as
 * busy and cannot be chosen; free teachers are listed first, with how many
 * periods they already have that day so cover is shared fairly.
 *
 * A substitute's access ends with that school day, and the screen says so.
 * Does not handle: marking a teacher absent for a whole day at once (cover
 * each period), or cover by someone who is not a teacher.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { Problem } from "@shared/ui/Problem";
import { listAllTeachingAssignments } from "@features/registry/api";
import { useLabels } from "@features/registry/useLabels";
import { useSchoolStructure } from "@features/registry/useSchoolStructure";
import {
  assignSubstitution,
  listSubstitutions,
  readSectionDay,
  readTeacherDay,
  withdrawSubstitution,
  type PeriodSession,
  type SectionDay,
  type Substitution,
} from "./api";
import { subjectColour } from "./subjectColours";
import { periodLabel, todayIso } from "./state";
import { useTimetableMessages } from "./useMessages";

type NamedSession = PeriodSession & { readonly subject_name?: string | null; readonly teacher_name?: string | null };

interface TeacherLoad {
  readonly id: string;
  readonly periods: readonly PeriodSession[];
}

const REASONS = ["leave", "sick", "training", "duty", "other"] as const;

export function SubstitutionPage() {
  const t = useTimetableMessages();
  const { t: tr } = useLanguage();
  const labels = useLabels();
  const { state: structure } = useSchoolStructure();
  const sections = structure.kind === "ready" ? structure.structure.sections : [];
  const subjectName = useMemo(
    () => new Map((structure.kind === "ready" ? structure.structure.subjects : []).map((row) => [row.id, row.display_name])),
    [structure],
  );

  const [date, setDate] = useState(todayIso());
  const [sectionId, setSectionId] = useState("");
  const [day, setDay] = useState<SectionDay | null>(null);
  const [teachers, setTeachers] = useState<readonly TeacherLoad[]>([]);
  const [substitutions, setSubstitutions] = useState<readonly Substitution[]>([]);
  const [session, setSession] = useState<NamedSession | null>(null);
  const [substitute, setSubstitute] = useState("");
  const [reason, setReason] = useState<(typeof REASONS)[number] | "">("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const chosenSection = sectionId || sections[0]?.id || "";

  const loadDay = useCallback(async () => {
    if (!chosenSection) return;
    try {
      const [loadedDay, subs] = await Promise.all([
        readSectionDay({ sectionId: chosenSection, date }),
        listSubstitutions(date),
      ]);
      setDay(loadedDay);
      setSubstitutions(subs.items);
    } catch (caught) {
      setError(caught);
    }
  }, [chosenSection, date]);

  // Every teacher's periods that day: who is free, and how loaded they are.
  const loadTeachers = useCallback(async () => {
    try {
      const assignments = await listAllTeachingAssignments();
      const ids = [...new Set(assignments.filter((row) => !row.to_date || row.to_date >= date).map((row) => row.staff_id))];
      const loads = await Promise.all(
        ids.map(async (id) => {
          const teacherDay = await readTeacherDay(id, date).catch(() => null);
          return { id, periods: teacherDay?.sessions ?? [] };
        }),
      );
      setTeachers(loads);
    } catch (caught) {
      setError(caught);
    }
  }, [date]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loads this screen's data
    void loadDay();
  }, [loadDay]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loads this screen's data
    void loadTeachers();
  }, [loadTeachers]);

  const pickDay = (next: string) => {
    setDate(next);
    setSession(null);
    setSubstitute("");
  };

  const coverFor = (row: PeriodSession) =>
    substitutions.find((item) => item.timetable_session_id === row.timetable_session_id && !item.withdrawn);

  const busyAt = (load: TeacherLoad, target: PeriodSession) =>
    load.periods.some(
      (period) =>
        !period.cancelled &&
        period.timetable_session_id !== target.timetable_session_id &&
        period.starts_at < target.ends_at &&
        target.starts_at < period.ends_at,
    );

  const choices = session
    ? teachers
        .filter((load) => load.id !== session.assigned_teacher_id)
        .map((load) => ({ ...load, busy: busyAt(load, session) }))
        .sort(
          (a, b) =>
            Number(a.busy) - Number(b.busy) ||
            a.periods.length - b.periods.length ||
            labels.person(a.id).localeCompare(labels.person(b.id)),
        )
    : [];

  const assign = async () => {
    if (!session || !substitute || !reason) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const why = reason === "other" ? note.trim() : [t(`timetable.substitution.reason.${reason}`), note.trim()].filter(Boolean).join(" – ");
      await assignSubstitution({ date, slotId: session.slot_id, teacherId: substitute, reason: why });
      setNotice(`${labels.person(substitute)} ${t("timetable.substitution.covers")} ${session.slot_code}.`);
      setSession(null);
      setSubstitute("");
      setReason("");
      setNote("");
      await Promise.all([loadDay(), loadTeachers()]);
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  };

  const withdraw = async (row: Substitution) => {
    setBusy(true);
    setError(null);
    try {
      await withdrawSubstitution(row.id, row.version);
      setNotice(t("timetable.substitution.withdrawn"));
      await Promise.all([loadDay(), loadTeachers()]);
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  };

  const sessions = (day?.sessions ?? []) as readonly NamedSession[];
  const active = substitutions.filter((row) => !row.withdrawn);
  const reasonReady = reason !== "" && (reason !== "other" || note.trim() !== "");

  return (
    <section aria-labelledby="substitution-title">
      <h2 id="substitution-title">{t("timetable.substitution.title")}</h2>
      <p className="hint">{t("timetable.substitution.expires")}</p>

      <div className="inline-fields">
        <label>
          {t("timetable.schedule.date")}
          <input type="date" value={date} onChange={(event) => pickDay(event.target.value)} />
        </label>
        <label>
          {t("timetable.editor.section")}
          <select value={chosenSection} onChange={(event) => {
              setSectionId(event.target.value);
              setSession(null);
            }}>
            {sections.map((row) => (
              <option key={row.id} value={row.id}>
                {row.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {notice ? (
        <p role="status" className="notice-success">
          {notice}
        </p>
      ) : null}
      <Problem error={error} />

      <h3>{t("timetable.substitution.step_period")}</h3>
      {day && !day.is_school_day ? (
        <p className="empty-state">{t("timetable.substitution.no_school")}</p>
      ) : sessions.length === 0 ? (
        <p className="empty-state">{t("timetable.substitution.no_periods")}</p>
      ) : (
        <ul className="cover-periods">
          {sessions.map((row) => {
            const cover = coverFor(row);
            const subject = row.subject_name ?? subjectName.get(row.subject_id) ?? "";
            const selected = session?.timetable_session_id === row.timetable_session_id;
            return (
              <li key={row.timetable_session_id} style={{ ["--subject" as string]: subjectColour(subject) }}>
                <button
                  type="button"
                  className={`cover-period${selected ? " selected" : ""}`}
                  aria-pressed={selected}
                  disabled={row.cancelled || cover !== undefined}
                  onClick={() => {
                    setSession(row);
                    setSubstitute("");
                  }}
                >
                  <span className="cover-when">
                    <strong>{row.slot_code}</strong>
                    <span>{periodLabel(row.starts_at_local, row.ends_at_local)}</span>
                  </span>
                  <span className="cover-what">
                    <strong>{subject}</strong>
                    <span>{row.teacher_name ?? labels.person(row.assigned_teacher_id)}</span>
                  </span>
                  <span className="cover-state">
                    {cover
                      ? `${t("timetable.substitution.covered_by")} ${labels.person(cover.substitute_teacher_id)}`
                      : row.cancelled
                        ? t("timetable.substitution.cancelled")
                        : ""}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}

      {session ? (
        <div className="cover-pick">
          <h3>
            {t("timetable.substitution.step_teacher")} {session.slot_code} ·{" "}
            {session.subject_name ?? subjectName.get(session.subject_id)}
          </h3>
          <div className="teacher-choices" role="radiogroup" aria-label={t("timetable.substitution.substitute")}>
            {choices.map((row) => (
              <label key={row.id} className={`teacher-choice${row.busy ? " busy" : ""}`}>
                <input
                  type="radio"
                  name="substitute"
                  value={row.id}
                  disabled={row.busy}
                  checked={substitute === row.id}
                  onChange={() => setSubstitute(row.id)}
                />
                <span>
                  <strong>{labels.person(row.id)}</strong>
                  <span className="hint">
                    {row.busy
                      ? t("timetable.substitution.busy")
                      : `${t("timetable.substitution.free")} · ${row.periods.length} ${t("timetable.substitution.periods_today")}`}
                  </span>
                </span>
              </label>
            ))}
          </div>

          <h3>{t("timetable.substitution.reason")}</h3>
          <div className="segmented" role="group" aria-label={t("timetable.substitution.reason")}>
            {REASONS.map((value) => (
              <button
                key={value}
                type="button"
                className="seg"
                aria-pressed={reason === value}
                onClick={() => setReason(value)}
              >
                {t(`timetable.substitution.reason.${value}`)}
              </button>
            ))}
          </div>
          <label>
            {reason === "other" ? t("timetable.substitution.reason_other") : t("timetable.substitution.note")}
            <input value={note} maxLength={200} onChange={(event) => setNote(event.target.value)} />
          </label>
          <div className="row-actions">
            <button type="button" disabled={busy || !substitute || !reasonReady} onClick={() => void assign()}>
              {substitute
                ? `${t("timetable.substitution.assign_to")} ${labels.person(substitute)}`
                : t("timetable.substitution.assign")}
            </button>
            <button type="button" className="quiet" onClick={() => setSession(null)}>
              {tr("details.cancel")}
            </button>
          </div>
        </div>
      ) : null}

      <h3>{t("timetable.substitution.today")}</h3>
      {active.length === 0 ? (
        <p className="hint">{t("timetable.substitution.none")}</p>
      ) : (
        <ul className="charge-list">
          {active.map((row) => (
            <li key={row.id} data-testid="substitution">
              <div>
                <strong>
                  {labels.section(row.section_id)} · {subjectName.get(row.subject_id) ?? ""}
                </strong>
                <span className="hint">
                  {labels.person(row.substitute_teacher_id)} {t("timetable.substitution.instead_of")}{" "}
                  {labels.person(row.original_teacher_id)} · {row.reason}
                </span>
              </div>
              <button type="button" className="quiet" disabled={busy} onClick={() => void withdraw(row)}>
                {t("timetable.substitution.withdraw")}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
