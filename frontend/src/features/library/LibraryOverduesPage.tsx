/** Overdue queue for librarians. */

import { useCallback, useEffect, useState } from "react";
import { ApiError, TransportError } from "@shared/api/errors";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { listOverdues, type OverdueItemDTO } from "./api";

type LoadState =
  | { readonly status: "loading" }
  | { readonly status: "ready"; readonly items: readonly OverdueItemDTO[] }
  | { readonly status: "error"; readonly messageKey: string };

function defaultAsOf(): string {
  return "2026-09-02";
}

function toMessageKey(error: unknown): string {
  if (error instanceof ApiError) return error.messageKey;
  if (error instanceof TransportError) return "error.transport";
  return "error.transport";
}

export function LibraryOverduesPage() {
  const { t } = useLanguage();
  const [asOf, setAsOf] = useState(defaultAsOf);
  const [state, setState] = useState<LoadState>({ status: "loading" });

  const load = useCallback(async (date: string) => {
    setState({ status: "loading" });
    try {
      const page = await listOverdues(date);
      setState({ status: "ready", items: page.items });
    } catch (error) {
      setState({ status: "error", messageKey: toMessageKey(error) });
    }
  }, []);

  useEffect(() => {
    void load(asOf);
  }, [asOf, load]);

  return (
    <section>
      <h1>{t("library.overdues_title")}</h1>
      <label>
        {t("library.as_of")}
        <input
          type="date"
          value={asOf}
          onChange={(event) => setAsOf(event.target.value)}
          aria-label={t("library.as_of")}
        />
      </label>
      {state.status === "loading" && <p role="status">{t("ui.loading")}</p>}
      {state.status === "error" && (
        <p role="alert">
          {t(state.messageKey)}
          <button type="button" onClick={() => void load(asOf)}>
            {t("ui.retry")}
          </button>
        </p>
      )}
      {state.status === "ready" && state.items.length === 0 && <p>{t("ui.empty")}</p>}
      {state.status === "ready" && state.items.length > 0 && (
        <table>
          <caption>{t("library.overdues_title")}</caption>
          <thead>
            <tr>
              <th scope="col">{t("library.col_borrower")}</th>
              <th scope="col">{t("library.col_accession")}</th>
              <th scope="col">{t("library.due_date")}</th>
            </tr>
          </thead>
          <tbody>
            {state.items.map((row) => (
              <tr key={row.loan_id}>
                <th scope="row">{row.borrower_display_name}</th>
                <td>{row.accession_no}</td>
                <td>{row.due_date}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
