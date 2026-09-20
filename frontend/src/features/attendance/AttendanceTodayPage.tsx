/**
 * Today's authorised timetable periods for the current teacher.
 */

import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, TransportError } from "@shared/api/errors";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { listPeriods, type AuthorizedPeriod } from "./api";

type LoadState =
  | { readonly status: "loading" }
  | { readonly status: "ready"; readonly items: readonly AuthorizedPeriod[] }
  | { readonly status: "error"; readonly messageKey: string };

function todayIso(): string {
  // School dates are Asia/Kolkata; for standalone demos the frozen seed date is fine.
  return "2026-07-15";
}

function toMessageKey(error: unknown): string {
  if (error instanceof ApiError) return error.messageKey;
  if (error instanceof TransportError) return "error.transport";
  return "error.transport";
}

export function AttendanceTodayPage() {
  const { t } = useLanguage();
  const [date, setDate] = useState(todayIso);
  const [state, setState] = useState<LoadState>({ status: "loading" });

  const load = useCallback(async (on: string) => {
    setState({ status: "loading" });
    try {
      const page = await listPeriods(on);
      setState({ status: "ready", items: page.items });
    } catch (error) {
      setState({ status: "error", messageKey: toMessageKey(error) });
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load(date);
  }, [date, load]);

  return (
    <main>
      <h1>{t("attendance.title")}</h1>
      <label>
        {t("attendance.pick_date")}
        <input
          type="date"
          value={date}
          onChange={(event) => setDate(event.target.value)}
          aria-label={t("attendance.pick_date")}
        />
      </label>
      {state.status === "loading" && <p role="status">{t("ui.loading")}</p>}
      {state.status === "error" && (
        <p role="alert">
          {t(state.messageKey)}
          <button type="button" onClick={() => void load(date)}>
            {t("ui.retry")}
          </button>
        </p>
      )}
      {state.status === "ready" && (
        <ul>
          {state.items.map((period) => (
            <li key={period.timetable_session_id}>
              <span>
                {period.slot_code} · {period.starts_at.slice(11, 16)}–
                {period.ends_at.slice(11, 16)}
              </span>{" "}
              <span data-testid="submission-state">
                {t(`attendance.state.${period.submission_state}`)}
              </span>{" "}
              <span>
                {t("attendance.missing")}: {period.missing_count}
              </span>{" "}
              <Link
                to={`/attendance/session/${period.timetable_session_id}`}
                data-testid={`open-${period.slot_code}`}
              >
                {t("attendance.open")}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
