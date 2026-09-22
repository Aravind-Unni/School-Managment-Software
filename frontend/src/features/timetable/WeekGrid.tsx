/**
 * One week of a timetable: days across, periods down, each lesson a coloured
 * block. Shared by the pupil's week, a teacher's own week and a class's week,
 * so all three read the same way.
 *
 * Today is marked; a day with no lessons is greyed; a lesson can carry a note
 * (a subject the pupil does not take, a cover teacher) and a day can carry
 * events (a test that day). On a phone the days become tabs.
 *
 * Does not handle: loading (the page fetches its own days) or editing.
 */

import { useState, type CSSProperties, type ReactNode } from "react";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { useTimetableMessages } from "./useMessages";
import { subjectColour } from "./subjectColours";
import { periodLabel } from "./state";

export interface WeekSession {
  readonly slot_code: string;
  readonly section_id: string;
  readonly subject_id: string;
  readonly starts_at_local: string;
  readonly ends_at_local: string;
  readonly subject_name?: string | null;
  readonly teacher_name?: string | null;
  readonly substitute_name?: string | null;
  readonly section_label?: string | null;
  readonly cancelled: boolean;
}

export interface WeekDay {
  readonly date: string;
  readonly is_school_day: boolean;
  readonly reason_key?: string | null;
  readonly sessions: readonly { readonly session: WeekSession; readonly dimmed?: boolean; readonly note?: string }[];
}

export interface DayEvent {
  readonly key: string;
  readonly label: string;
  readonly strong?: boolean;
}

/** Monday of the week containing ``date``. */
export function weekStart(date: string): string {
  const day = new Date(`${date}T00:00:00Z`);
  day.setUTCDate(day.getUTCDate() - ((day.getUTCDay() + 6) % 7));
  return day.toISOString().slice(0, 10);
}

export function addDays(date: string, delta: number): string {
  const day = new Date(`${date}T00:00:00Z`);
  day.setUTCDate(day.getUTCDate() + delta);
  return day.toISOString().slice(0, 10);
}

export function WeekGrid({
  dates,
  days,
  today,
  events,
  secondLine = "teacher",
}: {
  readonly dates: readonly string[];
  readonly days: readonly WeekDay[];
  readonly today: string;
  readonly events?: (date: string) => readonly DayEvent[];
  /** What the small line under the subject says. */
  readonly secondLine?: "teacher" | "class";
}) {
  const { language } = useLanguage();
  const tt = useTimetableMessages();
  const [shownDay, setShownDay] = useState(() =>
    dates.includes(today) ? today : (dates[0] ?? today),
  );

  const slots = new Map<string, { code: string; from: string; to: string }>();
  for (const day of days) {
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
  const dayName = (date: string) =>
    new Date(`${date}T00:00:00`).toLocaleDateString(language === "ml" ? "ml-IN" : "en-IN", {
      weekday: "short",
      day: "numeric",
    });

  const cell = (date: string, code: string): ReactNode => {
    const day = days.find((row) => row.date === date);
    const found = day?.sessions.find((row) => row.session.slot_code === code);
    if (day && !day.is_school_day) {
      return <span className="lesson closed">{day.reason_key ? tt(day.reason_key) : "—"}</span>;
    }
    if (!found) return <span className="lesson empty">—</span>;
    const session = found.session;
    const subject = session.subject_name ?? "";
    const under =
      secondLine === "class"
        ? (session.section_label ?? "")
        : (session.substitute_name ?? session.teacher_name ?? "");
    return (
      <span
        className={`lesson${found.dimmed ? " not-mine" : ""}${session.cancelled ? " cancelled" : ""}`}
        style={{ "--subject": subjectColour(subject) } as CSSProperties}
      >
        <strong>{subject}</strong>
        <span className="hint">{under}</span>
        {session.cancelled ? (
          <span className="hint">{tt("timetable.schedule.cancelled")}</span>
        ) : null}
        {found.note ? <span className="hint">{found.note}</span> : null}
      </span>
    );
  };

  return (
    <>
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
      <div className="week-grid" style={{ "--days": dates.length } as CSSProperties}>
        <div className="week-head period-col" />
        {dates.map((date) => (
          <div
            key={date}
            className={`week-head${date === today ? " today" : ""}${date === shownDay ? " shown" : ""}`}
          >
            {dayName(date)}
            {(() => {
              const day = days.find((row) => row.date === date);
              return day && !day.is_school_day ? (
                <span className="hint">{tt("timetable.schedule.notSchoolDay")}</span>
              ) : null;
            })()}
            {(events?.(date) ?? []).map((event) => (
              <span key={event.key} className={`day-test${event.strong ? " exam" : ""}`}>
                {event.label}
              </span>
            ))}
          </div>
        ))}
        {periods.map((period) => (
          <div key={period.code} style={{ display: "contents" }}>
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
    </>
  );
}
