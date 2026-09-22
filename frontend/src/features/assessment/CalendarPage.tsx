/**
 * The school month as the viewer has it: a pupil sees the subjects they take,
 * a teacher the classes they teach, the office every class. Days the school is
 * closed are greyed.
 *
 * Tapping a day opens that day in order: the viewer's own periods, with any
 * test or exam shown inside the period it falls in, and anything without a
 * period (an assignment to hand in) listed after.
 * Does not handle: adding events (teachers set tests on Assessments, the
 * office sets exams on Examinations).
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { request } from "@shared/api/client";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { Loading } from "@shared/ui/Loading";
import { Problem } from "@shared/ui/Problem";
import { PupilChooser, usePupilChoice } from "@features/registry/PupilChooser";
import { schoolToday } from "@features/registry/useSchoolStructure";
import { subjectColour } from "@features/timetable/subjectColours";
import { readStudentDay, readTeacherDay } from "@features/timetable/api";
import { periodLabel } from "@features/timetable/state";
import type { WeekSession } from "@features/timetable/WeekGrid";
import { useSession } from "@app/SessionContext";

interface Event {
  readonly assessment_id: string;
  readonly date: string;
  readonly time: string;
  readonly title: string;
  readonly type: string;
  readonly subject_name: string | null;
  readonly section_label: string | null;
  readonly section_id: string;
  readonly subject_id: string;
  readonly mine?: boolean;
}

/** A period on the chosen day, as the viewer has it. */
interface Period {
  readonly slot_code: string;
  readonly section_id: string;
  readonly subject_id: string;
  readonly starts_at_local: string;
  readonly ends_at_local: string;
  readonly subject_name: string | null;
  readonly with_whom: string | null;
  readonly cancelled: boolean;
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
  const { session } = useSession();
  const [month, setMonth] = useState(() => schoolToday().slice(0, 7));
  const [events, setEvents] = useState<readonly Event[]>([]);
  const [days, setDays] = useState<readonly CalendarDay[]>([]);
  const [chosenDay, setChosenDay] = useState<string | null>(null);
  const [periods, setPeriods] = useState<readonly Period[] | null>(null);
  const [onlyMine, setOnlyMine] = useState(true);
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

  // The day a viewer taps is their own day: a pupil's lessons, or a teacher's.
  useEffect(() => {
    if (chosenDay === null) return;
    const who = isFamily ? chosen?.id : session?.actor_id;
    if (!who) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loads this screen's data
    setPeriods(null);
    const asPeriod = (session: WeekSession, withWhom: string | null): Period => ({
      slot_code: session.slot_code,
      section_id: session.section_id,
      subject_id: session.subject_id,
      starts_at_local: session.starts_at_local,
      ends_at_local: session.ends_at_local,
      subject_name: session.subject_name ?? null,
      with_whom: withWhom,
      cancelled: session.cancelled,
    });
    const day = isFamily
      ? readStudentDay(who, chosenDay).then((read) =>
          read.sessions
            .filter((row) => row.enrolled)
            .map((row) => {
              const session: WeekSession = row.session;
              return asPeriod(session, session.substitute_name ?? session.teacher_name ?? null);
            }),
        )
      : readTeacherDay(who, chosenDay).then((read) =>
          read.sessions.map((row) => {
            const session: WeekSession = row;
            return asPeriod(session, session.section_label ?? null);
          }),
        );
    day.then(setPeriods, () => setPeriods([]));
  }, [chosenDay, isFamily, chosen?.id, session?.actor_id]);

  const closed = new Set(days.filter((row) => !row.is_school_day).map((row) => row.date));
  // A subject teacher's month is their own subject. The rest of their classes'
  // tests are one tick away, for anyone checking a week is not overloaded.
  const hasOthers = !isFamily && events.some((row) => row.mine === false);
  const shown = hasOthers && onlyMine ? events.filter((row) => row.mine !== false) : events;
  const eventsOn = (date: string) => shown.filter((row) => row.date === date);
  const today = schoolToday();
  const weekdays = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"] as const;
  const monthName = new Date(`${month}-01T00:00:00`).toLocaleDateString(language === "ml" ? "ml-IN" : "en-IN", {
    month: "long",
    year: "numeric",
  });
  const selected = chosenDay ? eventsOn(chosenDay) : [];
  /** A test sits in a period only if it is that class's lesson in that subject. */
  const happensIn = (event: Event, period: Period) =>
    event.section_id === period.section_id &&
    event.subject_id === period.subject_id &&
    event.time >= period.starts_at_local &&
    event.time < period.ends_at_local;

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
      {hasOthers ? (
        <label className="inline">
          <input
            type="checkbox"
            checked={!onlyMine}
            onChange={(event) => setOnlyMine(!event.target.checked)}
          />
          {t("calendar.show_all_classes")}
        </label>
      ) : null}
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
                  className={`month-event${row.type === "exam" ? " exam" : ""}${
                    !isFamily && row.mine === false ? " not-mine" : ""
                  }`}
                  title={`${row.section_label ?? ""} ${row.title}`.trim()}
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
          {closed.has(chosenDay) ? (
            <p className="hint">{t("calendar.closed")}</p>
          ) : periods === null ? (
            <Loading />
          ) : periods.length === 0 && selected.length === 0 ? (
            <p className="hint">{t("calendar.nothing")}</p>
          ) : (
            <ol className="day-timeline">
              {periods.map((period) => {
                const inThisPeriod = selected.filter((row) => happensIn(row, period));
                return (
                  <li
                    key={period.slot_code}
                    className={period.cancelled ? "cancelled" : ""}
                    style={{ borderColor: subjectColour(period.subject_name ?? "") }}
                  >
                    <span className="hint">{periodLabel(period.starts_at_local, period.ends_at_local)}</span>
                    <div>
                      <strong>{period.subject_name}</strong>
                      <span className="hint">{period.with_whom}</span>
                      {inThisPeriod.map((row) => (
                        <span
                          key={row.assessment_id}
                          className={row.type === "exam" ? "attention" : "day-test"}
                        >
                          {row.title || t(`assessments.type.${row.type}`)} ·{" "}
                          {t(`assessments.type.${row.type}`)}
                        </span>
                      ))}
                    </div>
                  </li>
                );
              })}
              {selected
                .filter((row) => !periods.some((period) => happensIn(row, period)))
                .map((row) => (
                  <li key={row.assessment_id} style={{ borderColor: subjectColour(row.subject_name ?? "") }}>
                    <span className="hint">{row.time}</span>
                    <div>
                      <strong>
                        {row.subject_name} · {row.title || t(`assessments.type.${row.type}`)}
                      </strong>
                      <span className="hint">
                        {t(`assessments.type.${row.type}`)}
                        {isFamily ? "" : ` · ${row.section_label ?? ""}`}
                      </span>
                    </div>
                  </li>
                ))}
            </ol>
          )}
        </div>
      ) : null}
    </section>
  );
}

export default CalendarPage;
