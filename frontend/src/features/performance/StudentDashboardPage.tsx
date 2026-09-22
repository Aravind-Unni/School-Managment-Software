/**
 * How one pupil is getting on: their average across published marks, the share
 * of lessons they have attended, and anything a teacher has been asked to
 * follow up.
 *
 * A figure nobody can act on is not shown: a measure without enough marks
 * behind it yet is left out rather than printed as "insufficient data", and
 * the machinery behind it (status codes, rule ids, definition versions) never
 * reaches the page.
 *
 * Does not handle: per-topic breakdown (M06 has no topic data yet) or raising
 * a warning, which is the at-risk list's work.
 */

import { useEffect, useState } from "react";
import { fetchAll } from "@shared/api/client";
import { listMyStudents, type StudentRecord } from "@features/registry/api";
import { useSession } from "@app/SessionContext";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { fetchDashboard, type DashboardDTO } from "./api";
import { performanceErrorMessage } from "./loadError";
import { performanceMessages } from "./locales/messages";
import { Loading } from "@shared/ui/Loading";

export function StudentDashboardPage() {
  const { language } = useLanguage();
  const t = performanceMessages[language];
  const { session } = useSession();
  const [students, setStudents] = useState<StudentRecord[]>([]);
  const [studentId, setStudentId] = useState("");
  const [data, setData] = useState<DashboardDTO | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    // Parents and pupils get their own children; staff get the directory.
    listMyStudents()
      .then(async (mine) =>
        mine.length > 0
          ? mine.map((row) => ({ ...row, status: "active" }) as unknown as StudentRecord)
          : fetchAll<StudentRecord>("/api/v1/students"),
      )
      .then((rows) => {
        if (cancelled) return;
        setStudents(rows);
        const actorDefault =
          session?.actor_id && rows.some((row) => row.id === session.actor_id)
            ? session.actor_id
            : (rows[0]?.id ?? "");
        setStudentId((current) => current || actorDefault);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(performanceErrorMessage(err, t["performance.denied"]));
      });
    return () => {
      cancelled = true;
    };
  }, [session?.actor_id, t]);

  useEffect(() => {
    if (!studentId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- loads this screen's data
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    fetchDashboard(studentId)
      .then((dto) => {
        if (!cancelled) {
          setData(dto);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(performanceErrorMessage(err, t["performance.denied"]));
          setData(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [studentId, t]);

  // Percentages a family can act on. A measure still gathering marks, or one
  // with no number behind it, says nothing and is left out.
  const shown = (data?.metrics ?? []).filter(
    (metric) => metric.status !== "insufficient_data" && metric.value !== null,
  );
  const open = (data?.warnings ?? []).filter((warning) => warning.state !== "dismissed");

  return (
    <section>
      <h1>{t["performance.title"]}</h1>
      {students.length > 1 && (
        <label>
          {t["performance.student_label"]}
          <select value={studentId} onChange={(event) => setStudentId(event.target.value)}>
            {students.map((row) => (
              <option key={row.id} value={row.id}>
                {row.display_name}
              </option>
            ))}
          </select>
        </label>
      )}
      {loading && <Loading />}
      {error && <p role="alert">{error}</p>}
      {!loading && !error && data && shown.length === 0 && (
        <p className="empty-state">{t["performance.empty"]}</p>
      )}
      {data && shown.length > 0 && (
        <div className="stat-row">
          {shown.map((metric) => (
            <div className="stat" key={metric.code}>
              <span className="stat-value">
                {metric.value === null ? "—" : `${Math.round(Number(metric.value))}%`}
              </span>
              <span className="hint">
                {t[`performance.metric.${metric.code}` as keyof typeof t] ?? metric.code}
              </span>
            </div>
          ))}
        </div>
      )}
      {data && shown.length > 0 ? (
        <p className="hint">{t["performance.window"]}</p>
      ) : null}
      {data && open.length > 0 && (
        <>
          <h3>{t["performance.following_up"]}</h3>
          <ul className="charge-list" aria-label={t["performance.following_up"]}>
            {open.map((warning) => (
              <li key={warning.id}>
                <div>
                  <strong>
                    {t[warning.explanation_key as keyof typeof t] ?? warning.explanation_key}
                  </strong>
                  <span className="hint">{t["performance.teacher_told"]}</span>
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
