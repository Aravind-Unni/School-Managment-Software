/**
 * A teacher's own dated schedule, including the periods they are covering.
 *
 * Today first, one period per row: this is the screen a teacher opens between
 * lessons on a phone.
 *
 * The staff id is typed rather than picked. M03 has no way to list staff -- the
 * frozen RegistryPort has no ``get_staff`` and no directory -- which is gap 3 in
 * contracts/M03/ports.md. When M01 is integrated the actor's own id comes from
 * the session and this field disappears for the common case.
 */

import { useCallback, useEffect, useState } from "react";
import { useSession } from "@app/SessionContext";
import { listAllStaff, type StaffMember } from "@features/registry/api";
import { readTeacherDay, type TeacherDay } from "./api";
import { SessionList } from "./SessionList";
import { todayIso, toErrorState, type LoadState } from "./state";
import { useTimetableMessages } from "./useMessages";

export function TeacherSchedulePage() {
  const t = useTimetableMessages();
  const { session } = useSession();
  // Opens on the signed-in teacher's own day; staff who may read other
  // teachers' schedules also get a list to choose from.
  const [staffId, setStaffId] = useState(session?.actor_id ?? "");
  const [staff, setStaff] = useState<readonly StaffMember[]>([]);
  useEffect(() => {
    listAllStaff().then(
      (rows) => setStaff(rows.filter((row) => !row.archived)),
      () => setStaff([]),
    );
  }, []);
  const [date, setDate] = useState(todayIso());
  const [state, setState] = useState<LoadState<TeacherDay | null>>({
    status: "ready",
    value: null,
  });

  const load = useCallback(async (staff: string, on: string) => {
    if (staff === "") {
      setState({ status: "ready", value: null });
      return;
    }
    setState({ status: "loading" });
    try {
      setState({ status: "ready", value: await readTeacherDay(staff, on) });
    } catch (error) {
      setState(toErrorState(error));
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load(staffId, date);
  }, [load, staffId, date]);

  return (
    <section aria-labelledby="timetable-teacher-heading">
      <h2 id="timetable-teacher-heading">{t("timetable.schedule.teacherTitle")}</h2>

      {staff.length > 1 ? (
        <label>
          {t("timetable.editor.teacher")}
          <select value={staffId} onChange={(event) => setStaffId(event.target.value)}>
            {staff.map((row) => (
              <option key={row.id} value={row.id}>
                {row.display_name}
              </option>
            ))}
          </select>
        </label>
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
          <button type="button" onClick={() => void load(staffId, date)}>
            {t("ui.retry")}
          </button>
        </div>
      )}

      {state.status === "ready" &&
        (state.value === null ? (
          <p role="status">{t("ui.empty")}</p>
        ) : (
          <SessionList
            sessions={state.value.sessions}
            isSchoolDay={state.value.is_school_day}
            reasonKey={state.value.reason_key}
            t={t}
            showClass
          />
        ))}
    </section>
  );
}
