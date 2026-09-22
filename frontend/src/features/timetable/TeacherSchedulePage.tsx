/**
 * A teacher's own week: the days across, the periods down, each lesson showing
 * the class it is with. Periods they are covering for someone else appear the
 * same way, because for that week they are theirs.
 *
 * Tests and exams the teacher has set that week appear under the day.
 * Staff who may read other teachers' weeks can switch teacher.
 * Does not handle: editing the timetable (see the planner).
 */

import { useCallback, useEffect, useState } from "react";
import { request } from "@shared/api/client";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { Loading } from "@shared/ui/Loading";
import { Problem } from "@shared/ui/Problem";
import { useSession } from "@app/SessionContext";
import { listAllStaff, type StaffMember } from "@features/registry/api";
import { readTeacherDay, type TeacherDay } from "./api";
import { todayIso } from "./state";
import { useTimetableMessages } from "./useMessages";
import { WeekGrid, addDays, weekStart, type WeekDay } from "./WeekGrid";

interface ScheduledItem {
  readonly assessment_id: string;
  readonly date: string;
  readonly type: string;
  readonly subject_name: string | null;
  readonly section_label: string | null;
}

export function TeacherSchedulePage() {
  const t = useTimetableMessages();
  const { t: tr, language } = useLanguage();
  const { session } = useSession();
  const [staffId, setStaffId] = useState(session?.actor_id ?? "");
  const [staff, setStaff] = useState<readonly StaffMember[]>([]);
  const [monday, setMonday] = useState(() => weekStart(todayIso()));
  const [days, setDays] = useState<readonly WeekDay[] | null>(null);
  const [scheduled, setScheduled] = useState<readonly ScheduledItem[]>([]);
  const [error, setError] = useState<unknown>(null);

  const dates = Array.from({ length: 6 }, (_, index) => addDays(monday, index));

  useEffect(() => {
    listAllStaff().then(
      (rows) => setStaff(rows.filter((row) => !row.archived)),
      () => setStaff([]),
    );
  }, []);

  const load = useCallback(async () => {
    if (staffId === "") return;
    setDays(null);
    setError(null);
    try {
      const [loaded, tests] = await Promise.all([
        Promise.all(dates.map((date) => readTeacherDay(staffId, date))),
        request<{ items: ScheduledItem[] }>("/api/v1/assessment-calendar", {
          query: { from: dates[0], to: dates[dates.length - 1] },
        }).catch(() => ({ items: [] as ScheduledItem[] })),
      ]);
      setDays(
        loaded.map((day: TeacherDay) => ({
          date: day.date,
          is_school_day: day.is_school_day,
          reason_key: day.reason_key,
          sessions: day.sessions.map((session) => ({ session })),
        })),
      );
      setScheduled(tests.items ?? []);
    } catch (caught) {
      setError(caught);
      setDays([]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reload per teacher and week
  }, [staffId, monday]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loads this screen's data
    void load();
  }, [load]);

  const today = todayIso();
  const dayName = (date: string) =>
    new Date(`${date}T00:00:00`).toLocaleDateString(language === "ml" ? "ml-IN" : "en-IN", {
      weekday: "short",
      day: "numeric",
    });

  return (
    <section aria-labelledby="teacher-week-title">
      <h2 id="teacher-week-title">{t("timetable.schedule.teacherTitle")}</h2>
      {staff.length > 1 ? (
        <label>
          {t("timetable.schedule.teacher")}
          <select value={staffId} onChange={(event) => setStaffId(event.target.value)}>
            {staff.map((row) => (
              <option key={row.id} value={row.id}>
                {row.display_name}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      <div className="toolbar">
        <div className="month-nav">
          <button type="button" className="secondary" onClick={() => setMonday(addDays(monday, -7))}>
            ←
          </button>
          <strong>
            {dayName(dates[0] ?? monday)} – {dayName(dates[5] ?? monday)}
          </strong>
          <button type="button" className="secondary" onClick={() => setMonday(addDays(monday, 7))}>
            →
          </button>
        </div>
        <button type="button" className="quiet" onClick={() => setMonday(weekStart(today))}>
          {t("timetable.schedule.thisWeek")}
        </button>
      </div>
      <Problem error={error} />
      {days === null ? (
        <Loading />
      ) : (
        <WeekGrid
          dates={dates}
          days={days}
          today={today}
          secondLine="class"
          events={(date) =>
            scheduled
              .filter((row) => row.date === date)
              .map((row) => ({
                key: row.assessment_id,
                label: `${row.section_label ?? ""} ${row.subject_name ?? ""} ${tr(`assessments.type.${row.type}`)}`,
                strong: row.type === "exam",
              }))
          }
        />
      )}
    </section>
  );
}
