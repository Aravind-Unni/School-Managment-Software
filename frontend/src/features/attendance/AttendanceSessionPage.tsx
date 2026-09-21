/**
 * Mark, save and submit one dated period register.
 *
 * Network failure never shows an unsaved submission as complete: submitSucceeded
 * flips only after a successful response.
 */

import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError, TransportError } from "@shared/api/errors";
import { useLanguage } from "@shared/i18n/LanguageContext";
import {
  createSession,
  saveSession,
  submitSession,
  type AttendanceSession,
  type WritableStatus,
} from "./api";

const STATUSES: readonly WritableStatus[] = ["present", "absent", "late", "excused"];

type PageState =
  | { readonly status: "loading" }
  | { readonly status: "ready"; readonly session: AttendanceSession }
  | { readonly status: "error"; readonly messageKey: string };

function toMessageKey(error: unknown): string {
  if (error instanceof ApiError) return error.messageKey;
  if (error instanceof TransportError) return "error.transport";
  return "error.transport";
}

export function AttendanceSessionPage() {
  const { t } = useLanguage();
  const { sessionId: timetableSessionId } = useParams<{ sessionId: string }>();
  const [page, setPage] = useState<PageState>({ status: "loading" });
  const [marks, setMarks] = useState<Record<string, WritableStatus>>({});
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [submitSucceeded, setSubmitSucceeded] = useState(false);

  const load = useCallback(async () => {
    if (!timetableSessionId) return;
    setPage({ status: "loading" });
    try {
      const session = await createSession(timetableSessionId);
      const initial: Record<string, WritableStatus> = {};
      for (const entry of session.entries) {
        if (entry.status !== "unmarked") {
          initial[entry.enrolment_id] = entry.status as WritableStatus;
        }
      }
      setMarks(initial);
      setSubmitSucceeded(session.state === "submitted");
      setPage({ status: "ready", session });
    } catch (error) {
      setPage({ status: "error", messageKey: toMessageKey(error) });
    }
  }, [timetableSessionId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  async function onSave() {
    if (page.status !== "ready") return;
    setBusy(true);
    setNotice(null);
    try {
      const entries = Object.entries(marks).map(([enrolment_id, status]) => ({
        enrolment_id,
        status,
      }));
      const session = await saveSession(page.session.id, page.session.version, entries);
      setPage({ status: "ready", session });
      setNotice(t("attendance.saved"));
    } catch (error) {
      setNotice(t(toMessageKey(error)));
    } finally {
      setBusy(false);
    }
  }

  async function onSubmit() {
    if (page.status !== "ready") return;
    setBusy(true);
    setNotice(null);
    setSubmitSucceeded(false);
    try {
      const session = await submitSession(
        page.session.id,
        page.session.version,
        `browser-${page.session.id}-${page.session.version}`,
      );
      setPage({ status: "ready", session });
      setSubmitSucceeded(true);
    } catch (error) {
      setSubmitSucceeded(false);
      setNotice(t("attendance.submit_failed") + " " + t(toMessageKey(error)));
    } finally {
      setBusy(false);
    }
  }

  function markAllPresent() {
    if (page.status !== "ready") return;
    const next: Record<string, WritableStatus> = {};
    for (const row of page.session.roster_snapshot) {
      next[row.enrolment_id] = "present";
    }
    setMarks(next);
  }

  if (page.status === "loading") return <p role="status">{t("ui.loading")}</p>;
  if (page.status === "error") {
    return (
      <p role="alert">
        {t(page.messageKey)}
        <button type="button" onClick={() => void load()}>
          {t("ui.retry")}
        </button>
      </p>
    );
  }

  const { session } = page;
  const readOnly = session.state === "submitted";

  return (
    <section>
      <p>
        <Link to="/attendance">{t("attendance.back")}</Link>
      </p>
      <h1>{t("nav.attendance_session")}</h1>
      <p data-testid="session-state">{t(`attendance.state.${session.state}`)}</p>
      {!readOnly && (
        <button type="button" onClick={markAllPresent} disabled={busy}>
          {t("attendance.mark_all_present")}
        </button>
      )}
      <ul>
        {session.roster_snapshot.map((row) => (
          <li key={row.enrolment_id}>
            <span>{row.display_name}</span>{" "}
            <select
              aria-label={row.display_name}
              disabled={readOnly || busy}
              value={marks[row.enrolment_id] ?? ""}
              onChange={(event) =>
                setMarks((previous) => ({
                  ...previous,
                  [row.enrolment_id]: event.target.value as WritableStatus,
                }))
              }
            >
              <option value="">{t("attendance.status.unmarked")}</option>
              {STATUSES.map((status) => (
                <option key={status} value={status}>
                  {t(`attendance.status.${status}`)}
                </option>
              ))}
            </select>
          </li>
        ))}
      </ul>
      {!readOnly && (
        <div>
          <button type="button" onClick={() => void onSave()} disabled={busy}>
            {t("attendance.save")}
          </button>
          <button type="button" onClick={() => void onSubmit()} disabled={busy}>
            {t("attendance.submit")}
          </button>
        </div>
      )}
      {notice !== null && <p role="status">{notice}</p>}
      {submitSucceeded && (
        <p role="status" data-testid="submit-complete">
          {t("attendance.state.submitted")}
        </p>
      )}
    </section>
  );
}
