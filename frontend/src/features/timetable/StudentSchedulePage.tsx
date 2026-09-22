/**
 * One pupil's week, as the pupil or their parent sees it: the days across, the
 * periods down, each lesson a coloured block with its teacher.
 *
 * A period teaching a subject the pupil does not take is shown struck through
 * rather than hidden, so the day has no unexplained gap. Tests and exams that
 * week appear under the day they fall on.
 * Does not handle: changing the timetable (see the planner).
 */

import { useCallback, useEffect, useState } from "react";
import { request } from "@shared/api/client";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { Loading } from "@shared/ui/Loading";
import { Problem } from "@shared/ui/Problem";
import { PupilChooser, usePupilChoice } from "@features/registry/PupilChooser";
import { readStudentDay, type StudentDay } from "./api";
import { todayIso } from "./state";
import { useTimetableMessages } from "./useMessages";
import { WeekGrid, addDays, weekStart, type WeekDay } from "./WeekGrid";

interface ScheduledItem {
  readonly assessment_id: string;
  readonly date: string;
  readonly title: string;
  readonly type: string;
  readonly subject_name: string | null;
}

export function StudentSchedulePage() {
  const t = useTimetableMessages();
  const { t: tr, language } = useLanguage();
  const { mine, chosen, setChosen } = usePupilChoice();
  const [monday, setMonday] = useState(() => weekStart(todayIso()));
  const [days, setDays] = useState<readonly WeekDay[] | null>(null);
  const [scheduled, setScheduled] = useState<readonly ScheduledItem[]>([]);
  const [error, setError] = useState<unknown>(null);

  const dates = Array.from({ length: 6 }, (_, index) => addDays(monday, index));

  const load = useCallback(async () => {
    if (!chosen) return;
    setDays(null);
    setError(null);
    try {
      const [loaded, tests] = await Promise.all([
        Promise.all(dates.map((date) => readStudentDay(chosen.id, date))),
        request<{ items: ScheduledItem[] }>("/api/v1/assessment-calendar", {
          query: { from: dates[0], to: dates[dates.length - 1], student_id: chosen.id },
        }).catch(() => ({ items: [] as ScheduledItem[] })),
      ]);
      setDays(
        loaded.map((day: StudentDay) => ({
          date: day.date,
          is_school_day: day.is_school_day,
          reason_key: day.reason_key,
          sessions: day.sessions.map((row) => ({
            session: row.session,
            dimmed: !row.enrolled,
            ...(row.enrolled ? {} : { note: t("timetable.schedule.notEnrolled") }),
          })),
        })),
      );
      setScheduled(tests.items ?? []);
    } catch (caught) {
      setError(caught);
      setDays([]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reload per pupil and week
  }, [chosen, monday]);

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
    <section aria-labelledby="week-title">
      <h2 id="week-title">{t("timetable.schedule.studentTitle")}</h2>
      <PupilChooser mine={mine} chosen={chosen} onChoose={setChosen} />
      {chosen ? (
        <>
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
              events={(date) =>
                scheduled
                  .filter((row) => row.date === date)
                  .map((row) => ({
                    key: row.assessment_id,
                    label: `${row.subject_name ?? ""} ${tr(`assessments.type.${row.type}`)}`,
                    strong: row.type === "exam",
                  }))
              }
            />
          )}
        </>
      ) : null}
    </section>
  );
}
