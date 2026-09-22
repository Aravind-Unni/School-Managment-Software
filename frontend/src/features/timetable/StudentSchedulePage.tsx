/**
 * One pupil's dated schedule, as the pupil or their guardian sees it.
 *
 * Today first, one period per row.
 *
 * The distinguishing thing this view does: a period teaching a subject the pupil
 * is not enrolled in is shown, and marked as not theirs. Hiding it would leave a
 * gap in the day with no explanation, and showing it unmarked would tell a pupil
 * to attend a lesson they are not in -- and later mark them absent from it.
 * Enrolment comes from Registry's subject-filtered roster, never from this
 * module's own guess.
 *
 * The pupil id is typed rather than picked, because the frozen RegistryPort
 * exposes no directory (gap 1 in contracts/M03/ports.md). Once M01 is
 * integrated, a pupil reading their OWN schedule needs no field at all: the id
 * comes from the session.
 */

import { useCallback, useEffect, useState } from "react";
import { listMyStudents } from "@features/registry/api";
import { StudentPicker, type PickedStudent } from "@features/registry/StudentPicker";
import { readStudentDay, type StudentDay } from "./api";
import { SessionList } from "./SessionList";
import { todayIso, toErrorState, type LoadState } from "./state";
import { useTimetableMessages } from "./useMessages";

export function StudentSchedulePage() {
  const t = useTimetableMessages();
  const [picked, setPicked] = useState<PickedStudent | null>(null);
  const [mine, setMine] = useState<readonly PickedStudent[]>([]);
  const studentId = picked?.id ?? "";

  // Parents and pupils see their own children straight away.
  useEffect(() => {
    listMyStudents().then(
      (rows) => {
        setMine(rows);
        if (rows[0]) setPicked(rows[0]);
      },
      () => setMine([]),
    );
  }, []);
  const [date, setDate] = useState(todayIso());
  const [state, setState] = useState<LoadState<StudentDay | null>>({
    status: "ready",
    value: null,
  });

  const load = useCallback(async (student: string, on: string) => {
    if (student === "") {
      setState({ status: "ready", value: null });
      return;
    }
    setState({ status: "loading" });
    try {
      setState({ status: "ready", value: await readStudentDay(student, on) });
    } catch (error) {
      setState(toErrorState(error));
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load(studentId, date);
  }, [load, studentId, date]);

  const day = state.status === "ready" ? state.value : null;

  return (
    <section aria-labelledby="timetable-student-heading">
      <h2 id="timetable-student-heading">{t("timetable.schedule.studentTitle")}</h2>

      {mine.length > 1 ? (
        <div className="child-switcher" role="tablist">
          {mine.map((row) => (
            <button
              key={row.id}
              type="button"
              role="tab"
              aria-selected={studentId === row.id}
              className={studentId === row.id ? "" : "secondary"}
              onClick={() => setPicked(row)}
            >
              {row.display_name}
            </button>
          ))}
        </div>
      ) : null}
      {mine.length === 0 ? (
        picked === null ? (
          <StudentPicker onPick={setPicked} />
        ) : (
          <div className="picked-person">
            <strong>{picked.display_name}</strong>
            <span className="hint">{picked.admission_no}</span>
            <button type="button" className="quiet" onClick={() => setPicked(null)}>
              {t("fees.collect.change_student")}
            </button>
          </div>
        )
      ) : null}

      <label>
        {t("timetable.schedule.date")}
        <input
          type="date"
          value={date}
          aria-label={t("timetable.schedule.date")}
          onChange={(event) => setDate(event.target.value)}
        />
      </label>

      {state.status === "loading" && <p role="status">{t("ui.loading")}</p>}

      {state.status === "error" && (
        <div role="alert">
          <p>{t(state.messageKey)}</p>
          {state.requestId !== null && (
            <p className="request-id">
              <code>{state.requestId}</code>
            </p>
          )}
          <button type="button" onClick={() => void load(studentId, date)}>
            {t("ui.retry")}
          </button>
        </div>
      )}

      {state.status === "ready" &&
        (day === null ? (
          <p role="status">{t("ui.empty")}</p>
        ) : (
          <SessionList
            sessions={day.sessions.map((row) => row.session)}
            isSchoolDay={day.is_school_day}
            reasonKey={day.reason_key}
            t={t}
            annotate={(session) =>
              day.sessions.find(
                (row) => row.session.timetable_session_id === session.timetable_session_id,
              )?.enrolled === false
                ? t("timetable.schedule.notEnrolled")
                : null
            }
          />
        ))}
    </section>
  );
}
