/**
 * Take one period's register: everyone starts present, tap the exceptions,
 * submit. Submit saves first, and never reports success unless the server
 * accepted it.
 */

import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { Problem } from "@shared/ui/Problem";
import {
  createSession,
  saveSession,
  submitSession,
  type AttendanceSession,
  type AuthorizedPeriod,
  type WritableStatus,
} from "./api";

const STATUSES: readonly WritableStatus[] = ["present", "absent", "late", "excused"];

export function AttendanceSessionPage() {
  const { t } = useLanguage();
  const { sessionId: timetableSessionId } = useParams<{ sessionId: string }>();
  const period = (useLocation().state as { period?: AuthorizedPeriod } | null)?.period;
  const [session, setSession] = useState<AttendanceSession | null>(null);
  const [marks, setMarks] = useState<Record<string, WritableStatus>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!timetableSessionId) return;
    setError(null);
    try {
      const loaded = await createSession(timetableSessionId);
      const initial: Record<string, WritableStatus> = {};
      for (const entry of loaded.entries) {
        // A fresh register starts with everyone present; the teacher marks exceptions.
        initial[entry.enrolment_id] =
          entry.status === "unmarked" ? "present" : (entry.status as WritableStatus);
      }
      setMarks(initial);
      setSession(loaded);
    } catch (caught) {
      setError(caught);
    }
  }, [timetableSessionId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loads this screen's data
    void load();
  }, [load]);

  if (error !== null && session === null) return <Problem error={error} />;
  if (session === null) return <p role="status">{t("ui.loading")}</p>;

  const readOnly = session.state === "submitted";
  const counts = STATUSES.map(
    (status) => [status, Object.values(marks).filter((value) => value === status).length] as const,
  );

  const entries = () =>
    Object.entries(marks).map(([enrolment_id, status]) => ({ enrolment_id, status }));

  const save = async (): Promise<AttendanceSession> => {
    const saved = await saveSession(session.id, session.version, entries());
    setSession(saved);
    return saved;
  };

  const run = async (work: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await work();
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="register" aria-labelledby="register-title">
      <p>
        <Link to="/attendance">{t("attendance.back")}</Link>
      </p>
      <h2 id="register-title">
        {period?.section_label ?? t("nav.attendance_session")}
        {period?.subject_name ? ` · ${period.subject_name}` : ""}
      </h2>
      {period ? (
        <p className="hint">
          {period.slot_code} {period.starts_at_local}–{period.ends_at_local}
        </p>
      ) : null}
      <p role="status" data-testid="session-state" className={readOnly ? "notice-success" : ""}>
        {readOnly ? t("attendance.submitted_note") : t("attendance.tap_hint")}
      </p>
      <div className="register-counts" aria-live="polite">
        {counts.map(([status, count]) => (
          <span key={status} className={`count count-${status}`}>
            {t(`attendance.status.${status}`)}: <strong>{count}</strong>
          </span>
        ))}
      </div>
      <ol className="register-list">
        {session.roster_snapshot.map((row) => (
          <li key={row.enrolment_id} className={`mark-${marks[row.enrolment_id] ?? "present"}`}>
            <span className="register-name">{row.display_name}</span>
            <div className="segmented" role="group" aria-label={row.display_name}>
              {STATUSES.map((status) => (
                <button
                  key={status}
                  type="button"
                  aria-pressed={marks[row.enrolment_id] === status}
                  disabled={readOnly || busy}
                  className={`seg seg-${status}`}
                  onClick={() => setMarks((previous) => ({ ...previous, [row.enrolment_id]: status }))}
                >
                  {t(`attendance.short.${status}`)}
                </button>
              ))}
            </div>
          </li>
        ))}
      </ol>
      {notice ? <p role="status" className="notice-success">{notice}</p> : null}
      <Problem error={error} />
      {!readOnly ? (
        <div className="sticky-actions">
          <button
            type="button"
            className="secondary"
            disabled={busy}
            onClick={() =>
              void run(async () => {
                await save();
                setNotice(t("attendance.saved"));
              })
            }
          >
            {t("attendance.save_draft")}
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() =>
              void run(async () => {
                const saved = await save();
                const submitted = await submitSession(
                  saved.id,
                  saved.version,
                  `browser-${saved.id}-${saved.version}`,
                );
                setSession(submitted);
                setNotice(t("attendance.submitted"));
              })
            }
          >
            {t("attendance.submit")}
          </button>
        </div>
      ) : null}
    </section>
  );
}
