/** Filtered audit viewer — redacted diffs only for school admins. */

import { useCallback, useEffect, useState } from "react";
import { toLoadError } from "@shared/api/errors";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { listAudit, type AuditRecord } from "./api";
import { Loading } from "@shared/ui/Loading";

type LoadState =
  | { readonly status: "loading" }
  | {
      readonly status: "ready";
      readonly items: readonly AuditRecord[];
      readonly nextCursor: string | null;
    }
  | { readonly status: "error"; readonly messageKey: string };

export function AuditViewerPage() {
  const { t } = useLanguage();
  const [action, setAction] = useState("");
  const [state, setState] = useState<LoadState>({ status: "loading" });

  const load = useCallback(async (cursor?: string, append = false) => {
    if (!append) setState({ status: "loading" });
    try {
      const trimmedAction = action.trim();
      const page = await listAudit({
        ...(trimmedAction.length > 0 ? { action: trimmedAction } : {}),
        ...(cursor !== undefined ? { cursor } : {}),
      });
      setState((previous) => ({
        status: "ready",
        items:
          append && previous.status === "ready"
            ? [...previous.items, ...page.items]
            : page.items,
        nextCursor: page.next_cursor,
      }));
    } catch (error) {
      setState({ status: "error", messageKey: toLoadError(error).messageKey });
    }
  }, [action]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  return (
    <section>
      <h1>{t("platform.audit_title")}</h1>
      <label>
        {t("platform.audit_action_filter")}
        <input value={action} onChange={(event) => setAction(event.target.value)} />
      </label>
      <button type="button" onClick={() => void load()}>
        {t("platform.apply_filters")}
      </button>
      {state.status === "loading" && <Loading />}
      {state.status === "error" && (
        <div role="alert">
          <p>{t(state.messageKey)}</p>
          <button type="button" onClick={() => void load()}>
            {t("ui.retry")}
          </button>
        </div>
      )}
      {state.status === "ready" && state.items.length === 0 && (
        <p role="status">{t("platform.audit_empty")}</p>
      )}
      {state.status === "ready" && state.items.length > 0 && (
        <ul>
          {state.items.map((record) => (
            <li key={record.id}>
              {record.occurred_at} · {record.action} · {record.aggregate_id}
            </li>
          ))}
        </ul>
      )}
      {state.status === "ready" && state.nextCursor !== null && (
        <button type="button" onClick={() => void load(state.nextCursor ?? undefined, true)}>
          {t("ui.load_more")}
        </button>
      )}
    </section>
  );
}
