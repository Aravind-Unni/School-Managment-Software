/**
 * The library counter: pick the student, then lend a book or take one back.
 *
 * Lend: search the catalogue, pick a copy that is on the shelf, confirm the
 * due date (two weeks by default). Return: the student's open loans are
 * listed with their titles; one tap returns a book in good condition.
 */

import { useCallback, useEffect, useState } from "react";
import { request } from "@shared/api/client";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { shortDate } from "@shared/format";
import { Problem } from "@shared/ui/Problem";
import { StudentPicker, type PickedStudent } from "@features/registry/StudentPicker";
import { schoolToday } from "@features/registry/useSchoolStructure";
import { issueLoan, returnLoan, searchTitles, type TitleDTO } from "./api";

interface CopyRow {
  readonly id: string;
  readonly accession_no: string;
  readonly state: string;
  readonly on_loan: boolean;
}

interface LoanRow {
  readonly id: string;
  readonly title_name: string | null;
  readonly accession_no: string | null;
  readonly due_date: string;
  readonly returned_at: string | null;
  readonly version: number;
}

const inTwoWeeks = () => {
  const [y, m, d] = schoolToday().split("-").map(Number);
  return new Date(Date.UTC(y ?? 2026, (m ?? 1) - 1, (d ?? 1) + 14)).toISOString().slice(0, 10);
};

export function LibraryDeskPage() {
  const { t, language } = useLanguage();
  const [student, setStudent] = useState<PickedStudent | null>(null);
  const [loans, setLoans] = useState<readonly LoanRow[]>([]);
  const [query, setQuery] = useState("");
  const [titles, setTitles] = useState<readonly TitleDTO[]>([]);
  const [title, setTitle] = useState<TitleDTO | null>(null);
  const [copies, setCopies] = useState<readonly CopyRow[]>([]);
  const [due, setDue] = useState(inTwoWeeks());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadLoans = useCallback(async (personId: string) => {
    const page = await request<{ items: LoanRow[] }>(`/api/v1/library/borrowers/${personId}/loans`);
    setLoans(page.items.filter((row) => row.returned_at === null));
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loads this screen's data
    if (student) void loadLoans(student.id).catch(setError);
  }, [student, loadLoans]);

  useEffect(() => {
    const needle = query.trim();
    if (needle.length < 2) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- loads this screen's data
      setTitles([]);
      return undefined;
    }
    const timer = window.setTimeout(() => {
      searchTitles({ q: needle }).then((page) => setTitles(page.items), () => setTitles([]));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    if (!title) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- loads this screen's data
      setCopies([]);
      return;
    }
    request<{ items: CopyRow[] }>("/api/v1/library/copies", { query: { title_id: title.id } }).then(
      (page) => setCopies(page.items),
      () => setCopies([]),
    );
  }, [title]);

  const run = async (work: () => Promise<void>, done: string) => {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await work();
      setNotice(done);
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  };

  const lend = (copy: CopyRow) =>
    run(async () => {
      if (!student) return;
      await issueLoan(
        { copy_id: copy.id, borrower_person_id: student.id, borrower_type: "student", due_date: due },
        crypto.randomUUID(),
      );
      setTitle(null);
      setQuery("");
      await loadLoans(student.id);
    }, t("library.desk.lent"));

  const takeBack = (loan: LoanRow) =>
    run(async () => {
      if (!student) return;
      await returnLoan(loan.id, {
        returned_at: new Date().toISOString(),
        condition: "ok",
        expected_version: loan.version,
      });
      await loadLoans(student.id);
    }, t("library.desk.returned"));

  const today = schoolToday();
  const onShelf = copies.filter((row) => !row.on_loan && row.state === "available");

  return (
    <section aria-labelledby="desk-title">
      <h2 id="desk-title">{t("library.desk.title")}</h2>
      {student === null ? (
        <StudentPicker onPick={setStudent} />
      ) : (
        <>
          <div className="picked-person">
            <strong>{student.display_name}</strong>
            <span className="hint">{student.admission_no}</span>
            <button type="button" className="quiet" onClick={() => setStudent(null)}>
              {t("fees.collect.change_student")}
            </button>
          </div>
          {notice ? <p role="status" className="notice-success">{notice}</p> : null}
          <Problem error={error} />
          <div className="two-column">
            <div>
              <h3>{t("library.desk.has_books")}</h3>
              {loans.length === 0 ? (
                <p className="hint">{t("overview.no_books")}</p>
              ) : (
                <ul className="charge-list">
                  {loans.map((loan) => (
                    <li key={loan.id}>
                      <div>
                        <strong>{loan.title_name ?? loan.accession_no}</strong>
                        <span className={loan.due_date < today ? "attention" : "hint"}>
                          {t("overview.book_due")} {shortDate(loan.due_date, language)}
                        </span>
                      </div>
                      <button type="button" disabled={busy} onClick={() => void takeBack(loan)}>
                        {t("library.desk.return")}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div>
              <h3>{t("library.desk.lend")}</h3>
              <label>
                {t("library.desk.find_book")}
                <input
                  type="search"
                  value={query}
                  onChange={(event) => {
                    setQuery(event.target.value);
                    setTitle(null);
                  }}
                />
              </label>
              {title === null ? (
                <ul className="picker-results">
                  {titles.map((row) => (
                    <li key={row.id}>
                      <button type="button" className="secondary" onClick={() => setTitle(row)}>
                        <strong>{row.name}</strong>
                        <span className="hint">{row.author}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <>
                  <p>
                    <strong>{title.name}</strong> <span className="hint">{title.author}</span>
                  </p>
                  <label>
                    {t("library.desk.due")}
                    <input type="date" value={due} min={today} onChange={(event) => setDue(event.target.value)} />
                  </label>
                  {onShelf.length === 0 ? (
                    <p role="status">{t("library.desk.none_on_shelf")}</p>
                  ) : (
                    <div className="row-actions">
                      {onShelf.map((copy) => (
                        <button key={copy.id} type="button" disabled={busy} onClick={() => void lend(copy)}>
                          {t("library.desk.lend_copy")} {copy.accession_no}
                        </button>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </>
      )}
    </section>
  );
}
