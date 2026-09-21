/**
 * Intervention task list for assigned staff.
 */

import { useEffect, useState } from "react";
import { fetchAll } from "@shared/api/client";
import type { StudentRecord } from "@features/registry/api";
import { useSession } from "@app/SessionContext";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { listInterventions, type InterventionDTO } from "./api";
import { performanceErrorMessage } from "./loadError";
import { performanceMessages } from "./locales/messages";

export function InterventionListPage() {
  const { language } = useLanguage();
  const t = performanceMessages[language];
  const { session } = useSession();
  const [students, setStudents] = useState<StudentRecord[]>([]);
  const [studentId, setStudentId] = useState("");
  const [items, setItems] = useState<readonly InterventionDTO[]>([]);
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
      // eslint-disable-next-line react-hooks/set-state-in-effect -- loads this screen's data
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    listInterventions(studentId)
      .then((page) => {
        if (!cancelled) {
          setItems([...page.items]);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(performanceErrorMessage(err, t["performance.denied"]));
          setItems([]);
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
      <h1>{t["performance.interventions_title"]}</h1>
      {students.length > 0 && (
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
      {!loading && !error && items.length === 0 && <p>{t["performance.empty"]}</p>}
      <ul>
        {items.map((item) => (
          <li key={item.id}>
            {item.goal} ({item.state}) — {t["performance.intervention_review"]}: {item.review_date}
          </li>
        ))}
      </ul>
    </section>
  );
}
