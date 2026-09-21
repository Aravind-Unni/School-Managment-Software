/** Librarian issue and return desk. */

import { useState } from "react";
import { ApiError, TransportError } from "@shared/api/errors";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { issueLoan, returnLoan, type LoanDTO } from "./api";

const DEFAULT_COPY = "b1c2d3e4-5f60-7788-9900-bbccddeef002";
const DEFAULT_BORROWER = "1e06f5ad-b530-51fa-a3be-e1bd65fd230c";

function toMessageKey(error: unknown): string {
  if (error instanceof ApiError) return error.messageKey;
  if (error instanceof TransportError) return "error.transport";
  return "error.transport";
}

export function LibraryDeskPage() {
  const { t } = useLanguage();
  const [copyId, setCopyId] = useState(DEFAULT_COPY);
  const [borrowerId, setBorrowerId] = useState(DEFAULT_BORROWER);
  const [dueDate, setDueDate] = useState("2026-10-01");
  const [issueSaving, setIssueSaving] = useState(false);
  const [issued, setIssued] = useState<LoanDTO | null>(null);
  const [issueErrorKey, setIssueErrorKey] = useState<string | null>(null);
  const [issueIdem] = useState(() => `desk-issue-${crypto.randomUUID()}`);

  const [returnLoanId, setReturnLoanId] = useState("");
  const [returnVersion, setReturnVersion] = useState("1");
  const [returnSaving, setReturnSaving] = useState(false);
  const [returned, setReturned] = useState<LoanDTO | null>(null);
  const [returnErrorKey, setReturnErrorKey] = useState<string | null>(null);

  async function onIssue(event: React.FormEvent) {
    event.preventDefault();
    setIssueSaving(true);
    setIssueErrorKey(null);
    setIssued(null);
    try {
      const loan = await issueLoan(
        {
          copy_id: copyId,
          borrower_person_id: borrowerId,
          borrower_type: "student",
          due_date: dueDate,
        },
        issueIdem,
      );
      setIssued(loan);
      setReturnLoanId(loan.id);
      setReturnVersion(String(loan.version));
    } catch (error) {
      setIssueErrorKey(toMessageKey(error));
    } finally {
      setIssueSaving(false);
    }
  }

  async function onReturn(event: React.FormEvent) {
    event.preventDefault();
    setReturnSaving(true);
    setReturnErrorKey(null);
    setReturned(null);
    try {
      const loan = await returnLoan(returnLoanId, {
        returned_at: new Date().toISOString(),
        condition: "ok",
        expected_version: Number(returnVersion),
      });
      setReturned(loan);
    } catch (error) {
      setReturnErrorKey(toMessageKey(error));
    } finally {
      setReturnSaving(false);
    }
  }

  return (
    <section>
      <h1>{t("library.desk_title")}</h1>
      <section>
        <h2>{t("library.issue_heading")}</h2>
        <form
          onSubmit={(event) => {
            void onIssue(event);
          }}
        >
          <label>
            {t("library.copy_id")}
            <input value={copyId} onChange={(e) => setCopyId(e.target.value)} required />
          </label>
          <label>
            {t("library.borrower_id")}
            <input
              value={borrowerId}
              onChange={(e) => setBorrowerId(e.target.value)}
              required
            />
          </label>
          <label>
            {t("library.due_date")}
            <input
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              required
            />
          </label>
          <button type="submit" disabled={issueSaving}>
            {issueSaving ? t("library.saving") : t("library.issue_submit")}
          </button>
        </form>
        {issueErrorKey && <p role="alert">{t(issueErrorKey)}</p>}
        {issued && (
          <p role="status">
            {t("library.issued")}: {issued.id} · {t("library.due_date")} {issued.due_date}
          </p>
        )}
      </section>
      <section>
        <h2>{t("library.return_heading")}</h2>
        <form
          onSubmit={(event) => {
            void onReturn(event);
          }}
        >
          <label>
            {t("library.loan_id")}
            <input
              value={returnLoanId}
              onChange={(e) => setReturnLoanId(e.target.value)}
              required
            />
          </label>
          <label>
            {t("library.loan_version")}
            <input
              type="number"
              min={1}
              value={returnVersion}
              onChange={(e) => setReturnVersion(e.target.value)}
              required
            />
          </label>
          <button type="submit" disabled={returnSaving}>
            {returnSaving ? t("library.saving") : t("library.return_submit")}
          </button>
        </form>
        {returnErrorKey && <p role="alert">{t(returnErrorKey)}</p>}
        {returned && (
          <p role="status">
            {t("library.returned")}: {returned.id}
          </p>
        )}
      </section>
    </section>
  );
}
