/**
 * A pupil's exam results for a term: the overall average and grade, how each
 * subject is going (average %, grade, number of tests), and every published
 * test with its marks.
 *
 * Only published marks appear; the school decides when marks are published.
 * Does not handle: ranks or class averages (not shared with families).
 */

import { useEffect, useState } from "react";
import { request } from "@shared/api/client";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { shortDate } from "@shared/format";
import { Loading } from "@shared/ui/Loading";
import { Problem } from "@shared/ui/Problem";
import { subjectColour } from "@features/timetable/subjectColours";
import { PupilChooser, usePupilChoice } from "./PupilChooser";

interface ResultRow {
  readonly assessment_id: string;
  readonly subject_id: string;
  readonly subject_name: string | null;
  readonly type: string | null;
  readonly title: string;
  readonly sat_on: string | null;
  readonly published_on: string | null;
  readonly marking_outcome: string | null;
  readonly score: string | null;
  readonly max_score: string;
  readonly percent: string | null;
  readonly grade: string | null;
}

interface SubjectRow {
  readonly subject_id: string;
  readonly subject_name: string | null;
  readonly tests: number;
  readonly average_percent: string;
  readonly grade: string | null;
}

interface Results {
  readonly term_id: string;
  readonly terms: readonly { readonly id: string; readonly name: string }[];
  readonly results: readonly ResultRow[];
  readonly subjects: readonly SubjectRow[];
  readonly overall: { readonly average_percent: string | null; readonly grade: string | null };
}

const mark = (value: string | null) => (value === null ? "—" : String(Number(value)));

export function ExamResultsPage() {
  const { t, language } = useLanguage();
  const { mine, chosen, setChosen } = usePupilChoice();
  const [termId, setTermId] = useState("");
  const [data, setData] = useState<Results | null>(null);
  const [error, setError] = useState<unknown>(null);

  // First load asks for the current term; the answer lists the year's terms.
  useEffect(() => {
    if (!chosen) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loads this screen's data
    setData(null);
    setError(null);
    request<Results>(`/api/v1/students/${chosen.id}/results`, { query: { term_id: termId || undefined } }).then(
      (loaded) => {
        setData(loaded);
        if (!termId) setTermId(loaded.term_id);
      },
      setError,
    );
  }, [chosen, termId]);

  const bySubject = new Map<string, ResultRow[]>();
  for (const row of data?.results ?? []) bySubject.set(row.subject_id, [...(bySubject.get(row.subject_id) ?? []), row]);

  return (
    <section aria-labelledby="results-title" className="family-page">
      <h2 id="results-title">{t("results.title")}</h2>
      <PupilChooser mine={mine} chosen={chosen} onChoose={setChosen} />
      {chosen ? (
        <>
          <div className="inline-fields">
            <label>
              {t("cards.term")}
              <select value={termId} onChange={(event) => setTermId(event.target.value)}>
                {(data?.terms ?? []).map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <Problem error={error} />
          {data === null ? (
            error ? null : <Loading />
          ) : data.results.length === 0 ? (
            <p className="empty-state">{t("results.none")}</p>
          ) : (
            <>
              <div className="stat-row">
                <div className="stat">
                  <span className="stat-value">{data.overall.average_percent}%</span>
                  <span className="hint">{t("results.overall")}</span>
                </div>
                {data.overall.grade ? (
                  <div className="stat">
                    <span className="stat-value">{data.overall.grade}</span>
                    <span className="hint">{t("results.grade")}</span>
                  </div>
                ) : null}
                <div className="stat">
                  <span className="stat-value">{data.results.length}</span>
                  <span className="hint">{t("results.tests")}</span>
                </div>
              </div>

              <h3>{t("results.by_subject")}</h3>
              <div className="table-scroll">
                <table className="bar-table">
                  <thead>
                    <tr>
                      <th scope="col">{t("results.subject")}</th>
                      <th scope="col">{t("results.average")}</th>
                      <th scope="col" className="num">{t("results.grade")}</th>
                      <th scope="col" className="num">{t("results.tests")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.subjects.map((row) => (
                      <tr key={row.subject_id}>
                        <th scope="row">{row.subject_name}</th>
                        <td>
                          <span className="bar" aria-hidden="true">
                            <span
                              style={{ width: `${Math.min(100, Number(row.average_percent))}%`, background: subjectColour(row.subject_name ?? "") }}
                            />
                          </span>
                          {row.average_percent}%
                        </td>
                        <td className="num">
                          <strong>{row.grade ?? "—"}</strong>
                        </td>
                        <td className="num">{row.tests}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <h3>{t("results.every_test")}</h3>
              {[...bySubject.entries()].map(([subjectId, rows]) => (
                <div key={subjectId} className="result-group">
                  <h4>{rows[0]?.subject_name}</h4>
                  <ul className="charge-list">
                    {rows.map((row) => (
                      <li key={row.assessment_id}>
                        <div>
                          <strong>
                            {row.title || (row.type ? t(`assessments.type.${row.type}`) : t("results.test"))}
                          </strong>
                          <span className="hint">
                            {row.type ? `${t(`assessments.type.${row.type}`)} · ` : ""}
                            {shortDate(row.sat_on ?? row.published_on, language)}
                          </span>
                        </div>
                        {row.marking_outcome === "absent" ? (
                          <span className="attention">{t("assessments.absent")}</span>
                        ) : (
                          <span className="result-mark">
                            {mark(row.score)} / {mark(row.max_score)}
                            <span className="hint"> · {row.percent}%</span>
                            {row.grade ? <strong> · {row.grade}</strong> : null}
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </>
          )}
        </>
      ) : null}
    </section>
  );
}

export default ExamResultsPage;
