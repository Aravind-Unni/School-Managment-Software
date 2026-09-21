/**
 * Paginated student directory backed by GET /api/v1/students.
 */

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { listStudents, type StudentRecord } from "./api";
import { loadErrorKey } from "./loadErrorKey";

type LoadState =
  | { readonly status: "loading"; readonly items: readonly StudentRecord[] }
  | {
      readonly status: "ready";
      readonly items: readonly StudentRecord[];
      readonly nextCursor: string | null;
    }
  | { readonly status: "error"; readonly messageKey: string; readonly items: readonly StudentRecord[] };

/** Lists students with search and cursor pagination. */
export function StudentDirectoryPage() {
  const { t } = useLanguage();
  const [searchText, setSearchText] = useState("");
  const [appliedQuery, setAppliedQuery] = useState<string | undefined>(undefined);
  const [state, setState] = useState<LoadState>({ status: "loading", items: [] });

  const loadFirstPage = useCallback(async (query: string | undefined) => {
    setState({ status: "loading", items: [] });
    try {
      const page = await listStudents(
        query && query.length > 0 ? { pageSize: 50, query } : { pageSize: 50 },
      );
      setState({
        status: "ready",
        items: page.items,
        nextCursor: page.next_cursor,
      });
    } catch (error) {
      setState({ status: "error", messageKey: loadErrorKey(error), items: [] });
    }
  }, []);

  const loadMore = useCallback(async () => {
    if (state.status !== "ready" || state.nextCursor === null) return;
    const cursor = state.nextCursor;
    const existing = state.items;
    setState({ status: "loading", items: existing });
    try {
      const page = await listStudents(
        appliedQuery !== undefined
          ? { cursor, pageSize: 50, query: appliedQuery }
          : { cursor, pageSize: 50 },
      );
      setState({
        status: "ready",
        items: [...existing, ...page.items],
        nextCursor: page.next_cursor,
      });
    } catch (error) {
      setState({ status: "error", messageKey: loadErrorKey(error), items: existing });
    }
  }, [appliedQuery, state]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadFirstPage(appliedQuery);
  }, [appliedQuery, loadFirstPage]);

  const onSearch = (event: FormEvent) => {
    event.preventDefault();
    const trimmed = searchText.trim();
    setAppliedQuery(trimmed.length > 0 ? trimmed : undefined);
  };

  const showEmpty =
    state.status !== "loading" && state.items.length === 0 && state.status !== "error";

  return (
    <main>
      <h1>{t("registry.students_title")}</h1>
      <form onSubmit={onSearch}>
        <label>
          {t("registry.search_label")}
          <input
            type="search"
            value={searchText}
            onChange={(event) => setSearchText(event.target.value)}
            aria-label={t("registry.search_label")}
          />
        </label>{" "}
        <button type="submit">{t("registry.search_submit")}</button>
      </form>
      {state.status === "loading" && state.items.length === 0 && (
        <p role="status">{t("ui.loading")}</p>
      )}
      {state.status === "error" && (
        <p role="alert">
          {t(state.messageKey)}{" "}
          <button type="button" onClick={() => void loadFirstPage(appliedQuery)}>
            {t("ui.retry")}
          </button>
        </p>
      )}
      {showEmpty && <p role="status">{t("ui.empty")}</p>}
      {state.items.length > 0 && (
        <table>
          <thead>
            <tr>
              <th scope="col">{t("registry.admission_no")}</th>
              <th scope="col">{t("registry.students_title")}</th>
              <th scope="col">{t("registry.status")}</th>
              <th scope="col">{t("registry.open_profile")}</th>
            </tr>
          </thead>
          <tbody>
            {state.items.map((student) => (
              <tr key={student.id}>
                <td>{student.admission_no}</td>
                <td>{student.display_name}</td>
                <td>{t(`registry.status.${student.status}`)}</td>
                <td>
                  <Link to={`/registry/students/${student.id}`}>{t("registry.open_profile")}</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {state.status === "ready" && state.nextCursor !== null && (
        <button type="button" onClick={() => void loadMore()} disabled={state.status !== "ready"}>
          {t("ui.load_more")}
        </button>
      )}
      {state.status === "loading" && state.items.length > 0 && (
        <p role="status">{t("ui.loading")}</p>
      )}
    </main>
  );
}
