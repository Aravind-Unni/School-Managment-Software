/** Catalogue search and availability for a selected title. */

import { useCallback, useEffect, useState } from "react";
import { ApiError, TransportError } from "@shared/api/errors";
import { useLanguage } from "@shared/i18n/LanguageContext";
import {
  getTitleAvailability,
  searchTitles,
  type AvailabilityView,
  type TitleDTO,
} from "./api";

type LoadState =
  | { readonly status: "loading" }
  | { readonly status: "ready"; readonly items: readonly TitleDTO[] }
  | { readonly status: "error"; readonly messageKey: string };

function toMessageKey(error: unknown): string {
  if (error instanceof ApiError) return error.messageKey;
  if (error instanceof TransportError) return "error.transport";
  return "error.transport";
}

export function LibraryCataloguePage() {
  const { t } = useLanguage();
  const [query, setQuery] = useState("");
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [availability, setAvailability] = useState<AvailabilityView | null>(null);
  const [availabilityErrorKey, setAvailabilityErrorKey] = useState<string | null>(null);

  const load = useCallback(async (q: string) => {
    setState({ status: "loading" });
    setSelectedId(null);
    setAvailability(null);
    setAvailabilityErrorKey(null);
    try {
      const page = await searchTitles(q.trim().length > 0 ? { q: q.trim() } : {});
      setState({ status: "ready", items: page.items });
    } catch (error) {
      setState({ status: "error", messageKey: toMessageKey(error) });
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loads this screen's data
    void load(query);
  // eslint-disable-next-line react-hooks/exhaustive-deps -- runs once for the initial load
  }, [load]);

  async function onSelectTitle(titleId: string) {
    setSelectedId(titleId);
    setAvailability(null);
    setAvailabilityErrorKey(null);
    try {
      const view = await getTitleAvailability(titleId);
      setAvailability(view);
    } catch (error) {
      setAvailabilityErrorKey(toMessageKey(error));
    }
  }

  return (
    <section>
      <h1>{t("library.catalogue_title")}</h1>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void load(query);
        }}
      >
        <label>
          {t("library.search")}
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            aria-label={t("library.search")}
          />
        </label>
        <button type="submit">{t("library.search_submit")}</button>
      </form>
      {state.status === "loading" && <p role="status">{t("ui.loading")}</p>}
      {state.status === "error" && (
        <p role="alert">
          {t(state.messageKey)}
          <button type="button" onClick={() => void load(query)}>
            {t("ui.retry")}
          </button>
        </p>
      )}
      {state.status === "ready" && state.items.length === 0 && <p>{t("ui.empty")}</p>}
      {state.status === "ready" && state.items.length > 0 && (
        <ul>
          {state.items.map((title) => (
            <li key={title.id}>
              <button type="button" onClick={() => void onSelectTitle(title.id)}>
                {title.name} · {title.author}
              </button>
            </li>
          ))}
        </ul>
      )}
      {selectedId && availabilityErrorKey && (
        <p role="alert">{t(availabilityErrorKey)}</p>
      )}
      {availability && (
        <p role="status">
          {t("library.availability")}: {availability.available} / {availability.total}
        </p>
      )}
    </section>
  );
}
