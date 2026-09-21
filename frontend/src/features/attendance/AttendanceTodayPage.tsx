/**
 * A teacher's periods for one school day, each with its register status and a
 * single clear action. Opens on today (school time); arrows move a day.
 */

import { useCallback, useEffect, useState, type CSSProperties } from "react";
import { Link } from "react-router-dom";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { shortDate } from "@shared/format";
import { Problem } from "@shared/ui/Problem";
import { schoolToday } from "@features/registry/useSchoolStructure";
import { subjectColour } from "@features/timetable/subjectColours";
import { listPeriods, type AuthorizedPeriod } from "./api";

function shiftDay(iso: string, days: number): string {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(y ?? 2026, (m ?? 1) - 1, (d ?? 1) + days)).toISOString().slice(0, 10);
}

export function AttendanceTodayPage() {
  const { t, language } = useLanguage();
  const today = schoolToday();
  const [date, setDate] = useState(today);
  const [items, setItems] = useState<readonly AuthorizedPeriod[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(async (on: string) => {
    setItems(null);
    setError(null);
    try {
      setItems((await listPeriods(on)).items);
    } catch (caught) {
      setError(caught);
      setItems([]);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loads this screen's data
    void load(date);
  }, [date, load]);

  const pending = (items ?? []).filter((row) => row.submission_state !== "submitted").length;

  return (
    <section aria-labelledby="attendance-title">
      <h2 id="attendance-title">{t("attendance.title")}</h2>
      <div className="day-nav">
        <button type="button" className="secondary" onClick={() => setDate(shiftDay(date, -1))}>
          {t("attendance.previous_day")}
        </button>
        <strong>
          {date === today ? `${t("attendance.today")}, ` : ""}
          {shortDate(date, language)}
        </strong>
        <button type="button" className="secondary" onClick={() => setDate(shiftDay(date, 1))}>
          {t("attendance.next_day")}
        </button>
        {date !== today ? (
          <button type="button" className="quiet" onClick={() => setDate(today)}>
            {t("attendance.back_to_today")}
          </button>
        ) : null}
      </div>
      <Problem error={error} />
      {items === null ? <p role="status">{t("ui.loading")}</p> : null}
      {items !== null && items.length === 0 && error === null ? (
        <p role="status">{t("attendance.no_periods")}</p>
      ) : null}
      {items !== null && items.length > 0 ? (
        <p className="hint">
          {pending === 0 ? t("attendance.all_done") : `${pending} ${t("attendance.to_take")}`}
        </p>
      ) : null}
      <ul className="period-cards">
        {(items ?? []).map((period) => {
          const done = period.submission_state === "submitted";
          return (
            <li
              key={period.timetable_session_id}
              className={done ? "done" : ""}
              style={{ "--subject": subjectColour(period.subject_name ?? "") } as CSSProperties}
            >
              <div className="period-when">
                <strong>{period.slot_code}</strong>
                <span>
                  {period.starts_at_local ?? period.starts_at.slice(11, 16)}–
                  {period.ends_at_local ?? period.ends_at.slice(11, 16)}
                </span>
              </div>
              <div className="period-what">
                <strong>{period.section_label ?? ""}</strong>
                <span>{period.subject_name ?? ""}</span>
                <span className="hint" data-testid="submission-state">
                  {t(`attendance.state.${period.submission_state}`)}
                  {!done && period.missing_count > 0
                    ? ` · ${period.missing_count} ${t("attendance.students")}`
                    : ""}
                </span>
              </div>
              <Link
                className={done ? "button-link secondary" : "button-link"}
                to={`/attendance/session/${period.timetable_session_id}`}
                state={{ period }}
                data-testid={`open-${period.slot_code}`}
              >
                {done ? t("attendance.view") : t("attendance.take")}
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
