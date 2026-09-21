/**
 * The dated period list every read-only schedule shares.
 *
 * Mobile shows today first and one period per row, because a phone is how a
 * teacher checks what is next between lessons. There is no week grid here on
 * purpose: the weekly view is the editor's job, and a five-column table on a
 * 360px screen is unreadable.
 *
 * A cancelled period is SHOWN, struck through and labelled, never dropped --
 * "the lesson is not on today" is the information a pupil needs, and an absent
 * row does not say it.
 */

import type { CSSProperties } from "react";
import type { PeriodSession } from "./api";
import { periodLabel, shortId } from "./state";
import { subjectColour } from "./subjectColours";

/** Names the server adds to each session (see views_schedules.with_names). */
type Named = PeriodSession & {
  readonly subject_name?: string | null;
  readonly teacher_name?: string | null;
  readonly substitute_name?: string | null;
  readonly section_label?: string | null;
};
import type { Translate } from "./useMessages";

export interface SessionListProps {
  readonly sessions: readonly PeriodSession[];
  readonly isSchoolDay: boolean;
  readonly reasonKey: string | null;
  readonly t: Translate;
  /** Rendered under a session: the pupil view marks subjects they do not take. */
  readonly annotate?: (session: PeriodSession) => string | null;
  /** Show the class instead of the teacher (a teacher's own schedule). */
  readonly showClass?: boolean;
}

export function SessionList({
  sessions,
  isSchoolDay,
  reasonKey,
  t,
  annotate,
  showClass = false,
}: SessionListProps) {
  if (!isSchoolDay) {
    return (
      <p role="status" className="timetable-empty">
        {t("timetable.schedule.notSchoolDay")}
        {reasonKey !== null ? ` — ${t(reasonKey)}` : ""}
      </p>
    );
  }

  if (sessions.length === 0) {
    return (
      <p role="status" className="timetable-empty">
        {t("ui.empty")}
      </p>
    );
  }

  return (
    <ol className="timetable-sessions">
      {sessions.map((raw) => {
        const session = raw as Named;
        const note = annotate?.(session) ?? null;
        const who = showClass
          ? session.section_label
          : (session.substitute_name ?? session.teacher_name);
        return (
          <li
            key={session.timetable_session_id}
            data-testid="session"
            style={{ "--subject": subjectColour(session.subject_name ?? "") } as CSSProperties}
          >
            <span className="timetable-period">{session.slot_code}</span>
            <span className="timetable-time">
              {periodLabel(session.starts_at_local, session.ends_at_local)}
            </span>
            <span
              className={session.cancelled ? "timetable-subject cancelled" : "timetable-subject"}
            >
              {session.subject_name ?? shortId(session.subject_id)}
            </span>
            {who ? <span className="timetable-who">{who}</span> : null}
            {session.cancelled && (
              <span className="timetable-flag">{t("timetable.schedule.cancelled")}</span>
            )}
            {session.substitute_teacher_id !== null && (
              <span className="timetable-flag">
                {t("timetable.schedule.substituteFor")}
              </span>
            )}
            {note !== null && <span className="timetable-note">{note}</span>}
          </li>
        );
      })}
    </ol>
  );
}
