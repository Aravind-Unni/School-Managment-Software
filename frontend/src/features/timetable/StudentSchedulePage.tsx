/**
 * One pupil's week: the days across, the periods down, each lesson a coloured
 * block with its subject and teacher. Today is marked, a day the school is
 * closed is greyed, and a period teaching a subject the pupil does not take is
 * shown struck through rather than hidden, so the day has no unexplained gap.
 *
 * A test or exam scheduled that day appears above the day's lessons.
 * On a phone the days become tabs, one day at a time.
 * Does not handle: changing the timetable (see the planner).
 */

import { useCallback, useEffect, useState, type CSSProperties } from "react";
import { request } from "@shared/api/client";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { Loading } from "@shared/ui/Loading";
import { Problem } from "@shared/ui/Problem";
import { PupilChooser, usePupilChoice } from "@features/registry/PupilChooser";
import { readStudentDay, type StudentDay } from "./api";
import { subjectColour } from "./subjectColours";
import { periodLabel, todayIso } from "./state";
import { useTimetableMessages } from "./useMessages";

interface ScheduledItem {
  readonly assessment_id: string;
  readonly date: string;
  readonly title: string;
  readonly type: string;
  readonly subject_name: string | null;
}

type NamedSession = StudentDay["sessions"][number]["session"] & {
  readonly subject_name?: string | null;
  readonly teacher_name?: string | null;
  readonly substitute_name?: string | null;
};

/** Monday of the week containing ``date``, as YYYY-MM-DD. */
function weekStart(date: string): string {
  const day = new Date(`${date}T00:00:00Z`);
  day.setUTCDate(day.getUTCDate() - ((day.getUTCDay() + 6) % 7));
  return day.toISOString().slice(0, 10);
}

function addDays(date: string, delta: number): string {
  const day = new Date(`${date}T00:00:00Z`);
  day.setUTCDate(day.getUTCDate() + delta);
  return day.toISOString().slice(0, 10);
}

export function StudentSchedulePage() {
  const t = useTimetableMessages();
  const { t: tr, language } = useLanguage();
  const { mine, chosen, setChosen } = usePupilChoice();
  const [monday, setMonday] = useState(() => weekStart(todayIso()));
  const [days, setDays] = useState<readonly StudentDay[] | null>(null);
  const [scheduled, setScheduled] = useState<readonly ScheduledItem[]>([]);
  const [shownDay, setShownDay] = useState(() => todayIso());
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
      setDays(loaded);
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

  // Every period code in the week, in time order: the rows of the grid.
  const slots = new Map<string, { code: string; from: string; to: string }>();
  for (const day of days ?? []) {
    for (const { session } of day.sessions) {
      if (!slots.has(session.slot_code)) {
        slots.set(session.slot_code, {
          code: session.slot_code,
          from: session.starts_at_local,
          to: session.ends_at_local,
        });
      }
    }
  }
  const periods = [...slots.values()].sort((a, b) => a.from.localeCompare(b.from));
  const today = todayIso();
  const dayName = (date: string) =>
    new Date(`${date}T00:00:00`).toLocaleDateString(language === "ml" ? "ml-IN" : "en-IN", {
      weekday: "short",
      day: "numeric",
    });

  const cell = (date: string, code: string) => {
    const day = (days ?? []).find((row) => row.date === date);
    const found = day?.sessions.find((row) => row.session.slot_code === code);
    if (!day?.is_school_day) return <span className="lesson closed">{day ? "—" : ""}</span>;
    if (!found) return <span className="lesson empty">—</span>;
    const session = found.session as NamedSession;
    const subject = session.subject_name ?? "";
    return (
      <span
        className={`lesson${found.enrolled ? "" : " not-mine"}${session.cancelled ? " cancelled" : ""}`}
        style={{ "--subject": subjectColour(subject) } as CSSProperties}
      >
        <strong>{subject}</strong>
        <span className="hint">{session.substitute_name ?? session.teacher_name ?? ""}</span>
        {found.enrolled ? null : <span className="hint">{t("timetable.schedule.notEnrolled")}</span>}
      </span>
    );
  };

  const testsOn = (date: string) => scheduled.filter((row) => row.date === date);

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

          <div className="day-tabs" role="tablist">
            {dates.map((date) => (
              <button
                key={date}
                type="button"
                role="tab"
                aria-selected={shownDay === date}
                className={shownDay === date ? "" : "secondary"}
                onClick={() => setShownDay(date)}
              >
                {dayName(date)}
              </button>
            ))}
          </div>

          {days === null ? (
            <Loading />
          ) : (
            <div className="week-grid" style={{ "--days": dates.length } as CSSProperties}>
              <div className="week-head period-col" />
              {dates.map((date) => (
                <div
                  key={date}
                  className={`week-head${date === today ? " today" : ""}${date === shownDay ? " shown" : ""}`}
                >
                  {dayName(date)}
                  {testsOn(date).map((row) => (
                    <span key={row.assessment_id} className={`day-test${row.type === "exam" ? " exam" : ""}`}>
                      {row.subject_name} {tr(`assessments.type.${row.type}`)}
                    </span>
                  ))}
                </div>
              ))}
              {periods.map((period) => (
                <div key={period.code} className="week-row" style={{ display: "contents" }}>
                  <div className="period-col">
                    <strong>{period.code}</strong>
                    <span className="hint">{periodLabel(period.from, period.to)}</span>
                  </div>
                  {dates.map((date) => (
                    <div
                      key={`${date}-${period.code}`}
                      className={`week-cell${date === today ? " today" : ""}${date === shownDay ? " shown" : ""}`}
                    >
                      {cell(date, period.code)}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
          {days !== null && periods.length === 0 ? (
            <p className="empty-state">{t("timetable.schedule.notSchoolDay")}</p>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
