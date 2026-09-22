/**
 * A pupil's attendance record: the overall percentage, then by subject and
 * month by month, for this term or the whole school year so far.
 *
 * Counts are periods (lessons). Late counts as attended; excused periods are
 * left out of the percentage. Does not handle: day-by-day registers or
 * correcting a mark (ask the class teacher).
 */

import { useEffect, useState } from "react";
import { request } from "@shared/api/client";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { Loading } from "@shared/ui/Loading";
import { Problem } from "@shared/ui/Problem";
import { subjectColour } from "@features/timetable/subjectColours";
import { PupilChooser, usePupilChoice } from "./PupilChooser";

interface Counts {
  readonly due: number;
  readonly marked: number;
  readonly present: number;
  readonly absent: number;
  readonly late: number;
  readonly excused: number;
  readonly percentage: string | null;
}

interface RecordData {
  readonly from_date: string;
  readonly to_date: string;
  readonly total: Counts;
  readonly by_subject: readonly (Counts & { readonly subject_id: string; readonly subject_name: string | null })[];
  readonly by_month: readonly (Counts & { readonly month: string })[];
}

type Range = "term" | "year";

function monthName(month: string, language: string): string {
  const [year, number] = month.split("-").map(Number);
  return new Date(year ?? 2026, (number ?? 1) - 1, 1).toLocaleDateString(language === "ml" ? "ml-IN" : "en-IN", {
    month: "long",
    year: "numeric",
  });
}

function Bar({ value, colour }: { readonly value: string | null; readonly colour?: string | undefined }) {
  const width = value === null ? 0 : Math.min(100, Number(value));
  const low = value !== null && width < 75;
  return (
    <span className="bar" aria-hidden="true">
      <span style={{ width: `${width}%`, background: low ? "var(--danger)" : (colour ?? "var(--navy)") }} />
    </span>
  );
}

const pct = (value: string | null) => (value === null ? "—" : `${Number(value).toFixed(0)}%`);

export function AttendanceRecordPage() {
  const { t, language } = useLanguage();
  const { mine, chosen, setChosen } = usePupilChoice();
  const [range, setRange] = useState<Range>("term");
  const [data, setData] = useState<RecordData | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    if (!chosen) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loads this screen's data
    setData(null);
    setError(null);
    request<RecordData>(`/api/v1/attendance/students/${chosen.id}/record`, { query: { range } }).then(
      setData,
      setError,
    );
  }, [chosen, range]);

  const table = (
    rows: readonly (Counts & { readonly key: string; readonly label: string; readonly colour?: string | undefined })[],
    heading: string,
  ) => (
    <div className="table-scroll">
      <table className="bar-table">
        <thead>
          <tr>
            <th scope="col">{heading}</th>
            <th scope="col">{t("record.attended")}</th>
            <th scope="col" className="num">{t("record.present")}</th>
            <th scope="col" className="num">{t("record.absent")}</th>
            <th scope="col" className="num">{t("record.late")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key}>
              <th scope="row">{row.label}</th>
              <td>
                <Bar value={row.percentage} colour={row.colour} />
                {pct(row.percentage)}
              </td>
              <td className="num">{row.present}</td>
              <td className={`num${row.absent > 0 ? " attention" : ""}`}>{row.absent}</td>
              <td className="num">{row.late}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  return (
    <section aria-labelledby="record-title" className="family-page">
      <h2 id="record-title">{t("record.title")}</h2>
      <PupilChooser mine={mine} chosen={chosen} onChoose={setChosen} />
      {chosen ? (
        <>
          <div className="segmented" role="group" aria-label={t("record.range")}>
            {(["term", "year"] as const).map((value) => (
              <button key={value} type="button" className="seg" aria-pressed={range === value} onClick={() => setRange(value)}>
                {t(`record.range.${value}`)}
              </button>
            ))}
          </div>
          <Problem error={error} />
          {data === null ? (
            error ? null : <Loading />
          ) : data.total.due === 0 ? (
            <p className="empty-state">{t("record.none")}</p>
          ) : (
            <>
              <div className="stat-row">
                <div className="stat">
                  <span className={`stat-value${Number(data.total.percentage) < 75 ? " attention" : ""}`}>
                    {pct(data.total.percentage)}
                  </span>
                  <span className="hint">{t("record.attended")}</span>
                </div>
                <div className="stat">
                  <span className="stat-value">{data.total.present}</span>
                  <span className="hint">{t("record.present")}</span>
                </div>
                <div className="stat">
                  <span className="stat-value">{data.total.absent}</span>
                  <span className="hint">{t("record.absent")}</span>
                </div>
                <div className="stat">
                  <span className="stat-value">{data.total.late}</span>
                  <span className="hint">{t("record.late")}</span>
                </div>
              </div>
              <p className="hint">{t("record.counting")}</p>
              <h3>{t("record.by_subject")}</h3>
              {table(
                data.by_subject.map((row) => ({
                  ...row,
                  key: row.subject_id,
                  label: row.subject_name ?? "—",
                  colour: subjectColour(row.subject_name ?? ""),
                })),
                t("results.subject"),
              )}
              <h3>{t("record.by_month")}</h3>
              {table(
                data.by_month.map((row) => ({ ...row, key: row.month, label: monthName(row.month, language) })),
                t("record.month"),
              )}
            </>
          )}
        </>
      ) : null}
    </section>
  );
}

export default AttendanceRecordPage;
