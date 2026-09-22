/**
 * Admit many pupils at once from the office's admissions spreadsheet.
 *
 * Choose the file (saved as CSV from Excel or Google Sheets); it is checked
 * straight away and every problem is listed by spreadsheet row. When nothing
 * is wrong, one button admits everyone: pupil, parent (siblings with the same
 * phone share one parent) and class. Nothing is half done: if any row has a
 * problem, nobody is admitted.
 *
 * Does not handle: parent logins (Accounts), or .xlsx files (save as CSV).
 */

import { useState, type ChangeEvent } from "react";
import { Link } from "react-router-dom";
import { request } from "@shared/api/client";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { Problem } from "@shared/ui/Problem";
import { Loading } from "@shared/ui/Loading";

interface ImportProblem {
  readonly row: number;
  readonly column: string;
  readonly message_key: string;
  readonly value: string;
}

interface ImportResult {
  readonly applied: boolean;
  readonly year: string | null;
  readonly ready: number;
  readonly per_class: Record<string, number>;
  readonly parents_with_phone: number;
  readonly parents_created?: number;
  readonly problems: readonly ImportProblem[];
}

const SAMPLE = [
  "Admission No,Student Name,Class,Date of Birth,Parent Name,Parent Phone,Parent Email",
  "2026-101,Anjali Nair,6A,31/05/2014,Suresh Nair,9847012345,",
  "2026-102,Arjun Nair,4B,02/01/2016,Suresh Nair,9847012345,",
  "2026-103,Fathima Rahman,7A,15/08/2013,Rahman K,9446011122,rahman@example.com",
].join("\n");

export function ImportStudentsPage() {
  const { t } = useLanguage();
  const [fileName, setFileName] = useState("");
  const [text, setText] = useState("");
  const [result, setResult] = useState<ImportResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [wrongType, setWrongType] = useState(false);

  const send = async (csv: string, apply: boolean) => {
    setBusy(true);
    setError(null);
    try {
      setResult(await request<ImportResult>("/api/v1/students/import", { method: "POST", body: { csv, apply } }));
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  };

  const choose = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    setResult(null);
    setWrongType(false);
    if (!file) return;
    setFileName(file.name);
    if (/\.(xlsx|xls|ods)$/i.test(file.name)) {
      setWrongType(true);
      setText("");
      return;
    }
    const body = await file.text();
    setText(body);
    await send(body, false);
  };

  const done = result?.applied === true;
  const problems = result?.problems ?? [];
  const sampleHref = `data:text/csv;charset=utf-8,${encodeURIComponent(SAMPLE)}`;

  return (
    <section aria-labelledby="import-title">
      <h2 id="import-title">{t("import.title")}</h2>
      <p>{t("import.intro")}</p>
      <ul className="hint">
        <li>{t("import.columns_required")}</li>
        <li>{t("import.columns_optional")}</li>
        <li>{t("import.siblings")}</li>
      </ul>
      <p>
        <a href={sampleHref} download="admissions-sample.csv">
          {t("import.sample")}
        </a>
      </p>

      {!done ? (
        <label className="file-pick">
          {t("import.choose")}
          <input type="file" accept=".csv,text/csv" disabled={busy} onChange={(event) => void choose(event)} />
        </label>
      ) : null}
      {wrongType ? (
        <p role="alert" className="attention">
          {t("import.save_as_csv")}
        </p>
      ) : null}
      {busy ? <Loading /> : null}
      <Problem error={error} />

      {result && !done ? (
        <div className="import-result">
          <h3>
            {fileName}: {result.ready} {t("import.ready")}
            {result.year ? ` · ${result.year}` : ""}
          </h3>
          {Object.keys(result.per_class).length > 0 ? (
            <ul className="chips">
              {Object.entries(result.per_class).map(([label, count]) => (
                <li key={label}>
                  {label}: {count}
                </li>
              ))}
            </ul>
          ) : null}
          {problems.length > 0 ? (
            <>
              <p role="alert" className="attention">
                {problems.length} {t("import.problems_found")}
              </p>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th scope="col">{t("import.row")}</th>
                      <th scope="col">{t("import.column")}</th>
                      <th scope="col">{t("import.problem")}</th>
                      <th scope="col">{t("import.value")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {problems.slice(0, 200).map((problem) => (
                      <tr key={`${problem.row}-${problem.column}-${problem.message_key}`}>
                        <td className="num">{problem.row}</td>
                        <td>{t(`import.col.${problem.column}`)}</td>
                        <td>{t(problem.message_key)}</td>
                        <td>{problem.value}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <button type="button" disabled={busy || result.ready === 0} onClick={() => void send(text, true)}>
              {t("import.admit")} {result.ready}
            </button>
          )}
        </div>
      ) : null}

      {done && result ? (
        <div className="notice-success" role="status">
          <p>
            <strong>
              {result.ready} {t("import.admitted")}
            </strong>
            {result.parents_created ? ` · ${result.parents_created} ${t("import.parents_added")}` : ""}
          </p>
          <p>
            <Link to="/registry/students">{t("import.see_students")}</Link>
            {" · "}
            <Link to="/settings/accounts">{t("import.parent_logins")}</Link>
          </p>
        </div>
      ) : null}
    </section>
  );
}

export default ImportStudentsPage;
