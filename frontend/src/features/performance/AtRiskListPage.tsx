/**
 * Teacher at-risk warning list with explanations (no prediction labels).
 */

import { useEffect, useState } from "react";
import { fetchAll } from "@shared/api/client";
import type { StudentRecord } from "@features/registry/api";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { fetchDashboard, type WarningSummary } from "./api";
import { performanceErrorMessage } from "./loadError";
import { performanceMessages } from "./locales/messages";

type ListedWarning = WarningSummary & { readonly studentLabel: string };

export function AtRiskListPage() {
  const { language } = useLanguage();
  const t = performanceMessages[language];
  const [warnings, setWarnings] = useState<ListedWarning[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const students = await fetchAll<StudentRecord>("/api/v1/students");
        const collected: ListedWarning[] = [];
        for (const student of students) {
          const dto = await fetchDashboard(student.id);
          for (const warning of dto.warnings) {
            collected.push({ ...warning, studentLabel: student.display_name });
          }
        }
        if (!cancelled) {
          setWarnings(collected);
          setError(null);
        }
      } catch (err: unknown) {
        if (!cancelled) setError(performanceErrorMessage(err, t["performance.denied"]));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [t]);

  return (
    <section>
      <h1>{t["performance.at_risk_title"]}</h1>
      {loading && <p role="status">{t["performance.loading"]}</p>}
      {error && <p role="alert">{error}</p>}
      {!loading && !error && warnings.length === 0 && <p>{t["performance.empty"]}</p>}
      <ul>
        {warnings.map((w) => (
          <li key={w.id}>
            {w.studentLabel}: {t[w.explanation_key as keyof typeof t] ?? w.explanation_key} - {w.state}
          </li>
        ))}
      </ul>
    </section>
  );
}
