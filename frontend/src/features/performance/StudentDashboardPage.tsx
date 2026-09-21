/**
 * Student progress dashboard with accessible metric table.
 */

import { useEffect, useState } from "react";
import { fetchAll } from "@shared/api/client";
import type { StudentRecord } from "@features/registry/api";
import { useSession } from "@app/SessionContext";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { fetchDashboard, type DashboardDTO } from "./api";
import { performanceErrorMessage } from "./loadError";
import { performanceMessages } from "./locales/messages";

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
    fetchAll<StudentRecord>("/api/v1/students")
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
      {loading && <p role="status">{t["performance.loading"]}</p>}
      {error && <p role="alert">{error}</p>}
      {!loading && !error && data && data.metrics.length === 0 && (
        <p>{t["performance.empty"]}</p>
      )}
      {data && data.metrics.length > 0 && (
        <table>
          <caption>{t["performance.title"]}</caption>
          <thead>
            <tr>
              <th scope="col">Metric</th>
              <th scope="col">Value</th>
              <th scope="col">Status</th>
            </tr>
          </thead>
          <tbody>
            {data.metrics.map((m) => (
              <tr key={m.code}>
                <th scope="row">
                  {t[`performance.metric.${m.code}` as keyof typeof t] ?? m.code}
                </th>
                <td>
                  {m.status === "insufficient_data"
                    ? t["performance.insufficient"]
                    : (m.value ?? "—")}
                </td>
                <td>{m.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {data && data.warnings.length > 0 && (
        <ul aria-label="warnings">
          {data.warnings.map((w) => (
            <li key={w.id}>
              {t[w.explanation_key as keyof typeof t] ?? w.explanation_key} ({w.state})
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
