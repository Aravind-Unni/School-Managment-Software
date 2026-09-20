/**
 * Student progress dashboard with accessible metric table.
 */

import { useEffect, useState } from "react";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { fetchDashboard, type DashboardDTO } from "./api";
import { performanceMessages } from "./locales/messages";

const DEFAULT_STUDENT = "1e06f5ad-b530-51fa-a3be-e1bd65fd230c";

export function StudentDashboardPage() {
  const { language } = useLanguage();
  const t = performanceMessages[language];
  const [data, setData] = useState<DashboardDTO | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    fetchDashboard(DEFAULT_STUDENT)
      .then((dto) => {
        if (!cancelled) {
          setData(dto);
          setError(null);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(
            err.message.includes("403") || err.message.includes("404")
              ? t["performance.denied"]
              : err.message,
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [t]);

  return (
    <main>
      <h1>{t["performance.title"]}</h1>
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
    </main>
  );
}
