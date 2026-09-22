/**
 * The school month: tests and exams that are coming, and the days the school
 * is closed. Families see their own child's class; teachers see their classes;
 * the office sees every class.
 *
 * Tap a day to see what is on it. Does not handle: adding events (teachers set
 * tests on Assessments, the office sets exams on Examinations).
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { request } from "@shared/api/client";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { Loading } from "@shared/ui/Loading";
import { Problem } from "@shared/ui/Problem";
import { PupilChooser, usePupilChoice } from "@features/registry/PupilChooser";
import { schoolToday } from "@features/registry/useSchoolStructure";
import { subjectColour } from "@features/timetable/subjectColours";

interface Event {
  readonly assessment_id: string;
  readonly date: string;
  readonly time: string;
  readonly title: string;
  readonly type: string;
  readonly subject_name: string | null;
  readonly section_label: string | null;
}

interface CalendarDay {
  readonly date: string;
  readonly is_school_day: boolean;
  readonly reason_key: string | null;
}

/** The dates of the month that contains ``anchor``, padded to whole weeks (Mon first). */
function monthGrid(anchor: string): string[] {
  const [year, month] = anchor.split("-").map(Number);
  const first = new Date(Date.UTC(year ?? 2026, (month ?? 1) - 1, 1));
  const start = new Date(first);
  start.setUTCDate(1 - ((first.getUTCDay() + 6) % 7));
  const days: string[] = [];
  for (let index = 0; index < 42; index += 1) {
    const day = new Date(start);
    day.setUTCDate(start.getUTCDate() + index);
    days.push(day.toISOString().slice(0, 10));
    if (index >= 34 && day.getUTCMonth() !== (month ?? 1) - 1) break;
  }
  return days;
}

function addMonths(anchor: string, delta: number): string {
  const [year, month] = anchor.split("-").map(Number);
  const moved = new Date(Date.UTC(year ?? 2026, (month ?? 1) - 1 + delta, 1));
  return moved.toISOString().slice(0, 7);
}

export function CalendarPage() {
  const { t, language } = useLanguage();
  const { mine, chosen, setChosen } = usePupilChoice();
  const [month, setMonth] = useState(() => schoolToday().slice(0, 7));
  const [events, setEvents] = useState<readonly Event[]>([]);
  const [days, setDays] = useState<readonly CalendarDay[]>([]);
  const [chosenDay, setChosenDay] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  const grid = useMemo(() => monthGrid(`${month}-01`), [month]);
  const isFamily = (mine?.length ?? 0) > 0;

  const load = useCallback(async () => {
    const from = grid[0] ?? `${month}-01`;
    const to = grid[grid.length - 1] ?? `${month}-28`;
    setLoading(true);
    setError(null);
    try {
      const [scheduled, calendar] = await Promise.all([
        request<{ items: Event[] }>("/api/v1/assessment-calendar", {
          query: { from, to, student_id: isFamily && chosen ? chosen.id : undefined },
        }),
        request<{ days: CalendarDay[] }>("/api/v1/calendar", { query: { from_date: from, to_date: to } }).catch(
          () => ({ days: [] }),
        ),
      ]);
      setEvents(scheduled.items ?? []);
      setDays(calendar.days ?? []);
    } catch (caught) {
      setError(caught);
    } finally {
      setLoading(false);
    }
  }, [grid, month, chosen, isFamily]);

  useEffect(() => {
    if (isFamily && chosen === null) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loads this screen's data
    void load();
  }, [load, isFamily, chosen]);

  const closed = new Set(days.filter((row) => !row.is_school_day).map((row) => row.date));
  const eventsOn = (date: string) => events.filter((row) => row.date === date);
  const today = schoolToday();
  const weekdays = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"] as const;
  const monthName = new Date(`${month}-01T00:00:00`).toLocaleDateString(language === "ml" ? "ml-IN" : "en-IN", {
    month: "long",
    year: "numeric",
  });
  const selected = chosenDay ? eventsOn(chosenDay) : [];

  return (
    <section aria-labelledby="calendar-title">
      <h2 id="calendar-title">{t("calendar.title")}</h2>
      <PupilChooser mine={mine} chosen={chosen} onChoose={setChosen} />
      <div className="toolbar">
        <div className="month-nav">
          <button type="button" className="secondary" onClick={() => setMonth(addMonths(month, -1))}>
            ←
          </button>
          <strong>{monthName}</strong>
          <button type="button" className="secondary" onClick={() => setMonth(addMonths(month, 1))}>
            →
          </button>
        </div>
        <span className="hint">{t("calendar.legend")}</span>
      </div>
      <Problem error={error} />
      {loading ? <Loading /> : null}

      <div className="month-grid" role="grid" aria-label={monthName}>
        {weekdays.map((day) => (
          <div key={day} className="month-head">
            {t(`calendar.day.${day}`)}
          </div>
        ))}
        {grid.map((date) => {
          const onDay = eventsOn(date);
          const outside = !date.startsWith(month);
          return (
            <button
              key={date}
              type="button"
              className={`month-cell${outside ? " outside" : ""}${closed.has(date) ? " closed" : ""}${
                date === today ? " today" : ""
              }${chosenDay === date ? " selected" : ""}`}
              onClick={() => setChosenDay(date)}
            >
              <span className="month-date">{Number(date.slice(8))}</span>
              {onDay.slice(0, 3).map((row) => (
                <span
                  key={row.assessment_id}
                  className={`month-event${row.type === "exam" ? " exam" : ""}`}
                  style={{ borderColor: subjectColour(row.subject_name ?? "") }}
                >
                  {row.subject_name}
                </span>
              ))}
              {onDay.length > 3 ? <span className="hint">+{onDay.length - 3}</span> : null}
            </button>
          );
        })}
      </div>

      {chosenDay ? (
        <div className="day-detail">
          <h3>{new Date(`${chosenDay}T00:00:00`).toLocaleDateString(language === "ml" ? "ml-IN" : "en-IN", {
            weekday: "long",
            day: "numeric",
            month: "long",
          })}</h3>
          {closed.has(chosenDay) ? <p className="hint">{t("calendar.closed")}</p> : null}
          {selected.length === 0 ? (
            <p className="hint">{t("calendar.nothing")}</p>
          ) : (
            <ul className="charge-list">
              {selected.map((row) => (
                <li key={row.assessment_id}>
                  <div>
                    <strong>
                      {row.subject_name} · {row.title || t(`assessments.type.${row.type}`)}
                    </strong>
                    <span className="hint">
                      {row.time}
                      {isFamily ? "" : ` · ${row.section_label ?? ""}`}
                    </span>
                  </div>
                  <span className={row.type === "exam" ? "attention" : "hint"}>
                    {t(`assessments.type.${row.type}`)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </section>
  );
}

export default CalendarPage;
