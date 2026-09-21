/**
 * One page per student: today's lessons, attendance, progress, fees, library
 * books and notices.
 *
 * Parents land on their own child (with a switcher for siblings); pupils on
 * themselves; staff search for any student they may see. Each panel loads on
 * its own and hides itself when the viewer may not see that part, so one
 * refused section never blanks the page.
 */

import { useEffect, useState, type CSSProperties, type ReactNode } from "react";
import { request } from "@shared/api/client";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { percent, rupees, shortDate } from "@shared/format";
import { subjectColour } from "@features/timetable/subjectColours";
import * as api from "./api";
import { StudentPicker, type PickedStudent } from "./StudentPicker";
import { schoolToday } from "./useSchoolStructure";

interface Chosen {
  readonly id: string;
  readonly display_name: string;
  readonly admission_no: string;
  readonly section_label?: string | null;
}

type Panel<T> = { kind: "loading" } | { kind: "ready"; data: T } | { kind: "hidden" };

/** Load one panel's data; a refusal or missing record hides the panel. */
function usePanel<T>(load: (() => Promise<T>) | null, key: string): Panel<T> {
  const [panel, setPanel] = useState<Panel<T>>({ kind: "loading" });
  useEffect(() => {
    if (load === null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- loads this screen's data
      setPanel({ kind: "hidden" });
      return undefined;
    }
    let cancelled = false;
    setPanel({ kind: "loading" });
    load().then(
      (data) => !cancelled && setPanel({ kind: "ready", data }),
      () => !cancelled && setPanel({ kind: "hidden" }),
    );
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reload when the student changes
  }, [key]);
  return panel;
}

function Card({ title, children }: { readonly title: string; readonly children: ReactNode }) {
  return (
    <section className="overview-card">
      <h3>{title}</h3>
      {children}
    </section>
  );
}

interface Session {
  readonly slot_code: string;
  readonly starts_at_local: string;
  readonly ends_at_local: string;
  readonly subject_name?: string | null;
  readonly teacher_name?: string | null;
  readonly substitute_name?: string | null;
  readonly cancelled: boolean;
}

function TodayPanel({ student }: { readonly student: Chosen }) {
  const { t } = useLanguage();
  const today = schoolToday();
  const panel = usePanel(
    () =>
      request<{ is_school_day: boolean; sessions: { session: Session; enrolled: boolean }[] }>(
        "/api/v1/student-schedule",
        { query: { student_id: student.id, date: today } },
      ),
    `today:${student.id}`,
  );
  if (panel.kind === "hidden") return null;
  return (
    <Card title={t("overview.today")}>
      {panel.kind === "loading" ? (
        <p className="hint">{t("ui.loading")}</p>
      ) : !panel.data.is_school_day || panel.data.sessions.length === 0 ? (
        <p className="hint">{t("overview.no_school_today")}</p>
      ) : (
        <ol className="lesson-list">
          {panel.data.sessions
            .filter((row) => row.enrolled)
            .map(({ session }) => (
              <li
                key={session.slot_code}
                style={{ "--subject": subjectColour(session.subject_name ?? "") } as CSSProperties}
                className={session.cancelled ? "cancelled" : ""}
              >
                <span className="lesson-time">
                  {session.starts_at_local}–{session.ends_at_local}
                </span>
                <strong>{session.subject_name ?? session.slot_code}</strong>
                <span className="hint">
                  {session.substitute_name ?? session.teacher_name ?? ""}
                  {session.cancelled ? ` · ${t("overview.cancelled")}` : ""}
                </span>
              </li>
            ))}
        </ol>
      )}
    </Card>
  );
}

function AttendancePanel({ student }: { readonly student: Chosen }) {
  const { t } = useLanguage();
  const today = schoolToday();
  const from = `${today.slice(0, 4)}-06-01`;
  const panel = usePanel(
    () =>
      request<{ present: number; absent: number; late: number; marked: number }>(
        "/api/v1/attendance/summary",
        { query: { student_id: student.id, from, to: today } },
      ),
    `attendance:${student.id}`,
  );
  if (panel.kind === "hidden") return null;
  if (panel.kind === "loading") return <Card title={t("overview.attendance")}>…</Card>;
  const { present, absent, late, marked } = panel.data;
  const share = percent(present + late, marked);
  return (
    <Card title={t("overview.attendance")}>
      <p className={`big-figure${share !== null && share < 75 ? " warn" : ""}`}>
        {share === null ? "—" : `${share}%`}
      </p>
      <p className="hint">
        {t("overview.periods_present")}: {present + late} · {t("overview.absent")}: {absent} ·{" "}
        {t("overview.late")}: {late}
      </p>
    </Card>
  );
}

function ProgressPanel({ student }: { readonly student: Chosen }) {
  const { t } = useLanguage();
  const panel = usePanel(
    () =>
      request<{ metrics: { code: string; value: string | null }[]; warnings: unknown[] }>(
        "/api/v1/performance/dashboard",
        { query: { scope: "student", window: "term", student_id: student.id } },
      ),
    `progress:${student.id}`,
  );
  if (panel.kind === "hidden") return null;
  if (panel.kind === "loading") return <Card title={t("overview.progress")}>…</Card>;
  const mean = panel.data.metrics.find((row) => row.code === "overall_mean")?.value;
  return (
    <Card title={t("overview.progress")}>
      <p className="big-figure">{mean ? `${Math.round(Number(mean))}%` : "—"}</p>
      <p className="hint">{t("overview.average_marks")}</p>
      {panel.data.warnings.length > 0 ? (
        <p className="attention">
          {panel.data.warnings.length} {t("overview.warnings_open")}
        </p>
      ) : null}
    </Card>
  );
}

export function FeesPanel({ student }: { readonly student: Chosen }) {
  const { t, language } = useLanguage();
  const panel = usePanel(
    () =>
      request<{
        balance: { outstanding_paise: number; overdue_paise: number; paid_paise: number };
        entries: { id: string; entry_type: string; amount_paise: number; posted_at: string; description_key: string }[];
      }>(`/api/v1/fees/students/${student.id}/fee-statement`),
    `fees:${student.id}`,
  );
  if (panel.kind === "hidden") return null;
  if (panel.kind === "loading") return <Card title={t("overview.fees")}>…</Card>;
  const { balance, entries } = panel.data;
  return (
    <Card title={t("overview.fees")}>
      <p className={`big-figure${balance.overdue_paise > 0 ? " warn" : ""}`}>
        {rupees(balance.outstanding_paise)}
      </p>
      <p className="hint">
        {t("overview.to_pay")}
        {balance.overdue_paise > 0
          ? ` · ${rupees(balance.overdue_paise)} ${t("overview.overdue")}`
          : ""}
      </p>
      <details>
        <summary>{t("overview.fee_history")}</summary>
        <ul className="plain-rows">
          {entries.map((row) => (
            <li key={row.id}>
              <span>{shortDate(row.posted_at, language)}</span>
              <span>{t(row.description_key || `fees.entry.${row.entry_type}`)}</span>
              <strong>{rupees(row.amount_paise)}</strong>
            </li>
          ))}
        </ul>
      </details>
    </Card>
  );
}

function LibraryPanel({ student }: { readonly student: Chosen }) {
  const { t, language } = useLanguage();
  const panel = usePanel(
    () =>
      request<{ items: { id: string; due_date: string; returned_at: string | null }[] }>(
        `/api/v1/library/borrowers/${student.id}/loans`,
      ),
    `library:${student.id}`,
  );
  if (panel.kind === "hidden") return null;
  if (panel.kind === "loading") return <Card title={t("overview.library")}>…</Card>;
  const open = panel.data.items.filter((row) => row.returned_at === null);
  const today = schoolToday();
  return (
    <Card title={t("overview.library")}>
      {open.length === 0 ? (
        <p className="hint">{t("overview.no_books")}</p>
      ) : (
        <ul className="plain-rows">
          {open.map((row) => (
            <li key={row.id}>
              <span>{t("overview.book_due")}</span>
              <strong className={row.due_date < today ? "attention" : ""}>
                {shortDate(row.due_date, language)}
              </strong>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function NoticesPanel() {
  const { t, language } = useLanguage();
  const panel = usePanel(
    () =>
      request<{ items: { id: string; title: string; body: string; published_at: string }[] }>(
        "/api/v1/notices/inbox",
      ),
    "notices",
  );
  if (panel.kind === "hidden") return null;
  if (panel.kind === "loading") return <Card title={t("overview.notices")}>…</Card>;
  if (panel.data.items.length === 0) return null;
  return (
    <Card title={t("overview.notices")}>
      {panel.data.items.slice(0, 5).map((row) => (
        <article key={row.id} className="notice">
          <h4>{row.title}</h4>
          <p className="hint">{shortDate(row.published_at, language)}</p>
          <p>{row.body}</p>
        </article>
      ))}
    </Card>
  );
}

export function StudentOverviewPage() {
  const { t } = useLanguage();
  const [mine, setMine] = useState<readonly api.MyStudent[] | null>(null);
  const [chosen, setChosen] = useState<Chosen | null>(null);

  useEffect(() => {
    api.listMyStudents().then(
      (rows) => {
        setMine(rows);
        if (rows[0]) setChosen(rows[0]);
      },
      () => setMine([]),
    );
  }, []);

  if (mine === null) return <p role="status">{t("ui.loading")}</p>;
  const isFamily = mine.length > 0;

  return (
    <section className="overview" aria-labelledby="overview-title">
      <h2 id="overview-title">{isFamily ? t("overview.title_family") : t("overview.title_staff")}</h2>
      {isFamily && mine.length > 1 ? (
        <div className="child-switcher" role="tablist" aria-label={t("overview.children")}>
          {mine.map((row) => (
            <button
              key={row.id}
              type="button"
              role="tab"
              aria-selected={chosen?.id === row.id}
              className={chosen?.id === row.id ? "" : "secondary"}
              onClick={() => setChosen(row)}
            >
              {row.display_name}
            </button>
          ))}
        </div>
      ) : null}
      {!isFamily ? (
        <StudentPicker onPick={(row: PickedStudent) => setChosen(row)} />
      ) : null}
      {chosen === null ? (
        <p role="status">{isFamily ? t("overview.no_children") : t("overview.pick_prompt")}</p>
      ) : (
        <>
          <header className="overview-person">
            <h3>{chosen.display_name}</h3>
            <p className="hint">
              {chosen.admission_no}
              {chosen.section_label ? ` · ${chosen.section_label}` : ""}
            </p>
          </header>
          <div className="overview-grid" key={chosen.id}>
            <TodayPanel student={chosen} />
            <AttendancePanel student={chosen} />
            <ProgressPanel student={chosen} />
            <FeesPanel student={chosen} />
            <LibraryPanel student={chosen} />
            {isFamily ? <NoticesPanel /> : null}
          </div>
        </>
      )}
    </section>
  );
}

export default StudentOverviewPage;
