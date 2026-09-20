/**
 * Teacher at-risk warning list with explanations (no prediction labels).
 */

import { useEffect, useState } from "react";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { fetchDashboard, type WarningSummary } from "./api";
import { performanceMessages } from "./locales/messages";

const DEFAULT_STUDENT = "1e06f5ad-b530-51fa-a3be-e1bd65fd230c";

export function AtRiskListPage() {
  const { language } = useLanguage();
  const t = performanceMessages[language];
  const [warnings, setWarnings] = useState<WarningSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDashboard(DEFAULT_STUDENT)
      .then((dto) => setWarnings(dto.warnings))
      .catch((err: Error) =>
        setError(
          err.message.includes("403") || err.message.includes("404")
            ? t["performance.denied"]
            : err.message,
        ),
      );
  }, [t]);

  return (
    <main>
      <h1>{t["performance.at_risk_title"]}</h1>
      {error && <p role="alert">{error}</p>}
      {!error && warnings.length === 0 && <p>{t["performance.empty"]}</p>}
      <ul>
        {warnings.map((w) => (
          <li key={w.id}>
            {t[w.explanation_key as keyof typeof t] ?? w.explanation_key} - {w.state}
          </li>
        ))}
      </ul>
    </main>
  );
}
