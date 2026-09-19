/**
 * The placeholder feature page.
 *
 * Proves the frontend half of the foundation end to end: it calls the real API
 * through the shared client, renders the error envelope via message keys, and
 * walks cursor pages. It owns no business meaning.
 */

import { useCallback, useEffect, useState } from "react";
import { ApiError, TransportError } from "@shared/api/errors";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { listNotes, type Note } from "./api";

type LoadState =
  | { readonly status: "loading" }
  | { readonly status: "ready"; readonly notes: readonly Note[]; readonly nextCursor: string | null }
  | { readonly status: "error"; readonly messageKey: string; readonly requestId: string | null };

/**
 * Map any thrown value to a renderable message key.
 *
 * A TransportError becomes a transport message, never a business one: telling a
 * user "you do not have permission" when the network dropped is worse than a
 * generic failure.
 */
function toMessageKey(error: unknown): { messageKey: string; requestId: string | null } {
  if (error instanceof ApiError) {
    return { messageKey: error.messageKey, requestId: error.requestId };
  }
  if (error instanceof TransportError) {
    return { messageKey: "error.transport", requestId: null };
  }
  return { messageKey: "error.transport", requestId: null };
}

export function DemoNotesPage() {
  const { t } = useLanguage();
  const [state, setState] = useState<LoadState>({ status: "loading" });

  const load = useCallback(async (cursor?: string) => {
    try {
      const page = await listNotes(cursor === undefined ? {} : { cursor });
      setState((previous) => ({
        status: "ready",
        notes:
          cursor === undefined || previous.status !== "ready"
            ? page.items
            : [...previous.notes, ...page.items],
        nextCursor: page.next_cursor,
      }));
    } catch (error) {
      setState({ status: "error", ...toMessageKey(error) });
    }
  }, []);

  useEffect(() => {
    // react-hooks/set-state-in-effect: fetching on mount and then setting state
    // is exactly what this rule discourages, and it is right that a data library
    // (or a router loader) would be better. The foundation deliberately ships no
    // data-fetching library yet -- that is a choice for the first real module to
    // make -- so the placeholder does it plainly and flags it here rather than
    // pretending the concern does not exist.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  if (state.status === "loading") {
    return <p role="status">{t("ui.loading")}</p>;
  }

  if (state.status === "error") {
    return (
      <div role="alert">
        <p>{t(state.messageKey)}</p>
        {state.requestId !== null && (
          <p className="request-id">
            <code>{state.requestId}</code>
          </p>
        )}
        <button type="button" onClick={() => void load()}>
          {t("ui.retry")}
        </button>
      </div>
    );
  }

  return (
    <section aria-labelledby="demo-heading">
      <h2 id="demo-heading">{t("nav.demo")}</h2>
      {state.notes.length === 0 ? (
        <p role="status">{t("ui.empty")}</p>
      ) : (
        <ul>
          {state.notes.map((note) => (
            <li key={note.id} data-testid="demo-note">
              <span>{note.body}</span>{" "}
              <small>v{note.version}</small>
            </li>
          ))}
        </ul>
      )}
      {state.nextCursor !== null && (
        <button type="button" onClick={() => void load(state.nextCursor ?? undefined)}>
          {t("ui.load_more")}
        </button>
      )}
    </section>
  );
}

export default DemoNotesPage;
