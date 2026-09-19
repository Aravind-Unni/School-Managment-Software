/**
 * Security settings: the caller's own sessions, and factor status.
 *
 * Shows only the CALLER's sessions. There is deliberately no way to view another
 * account's factor or sessions from here, because an administrator must never see
 * one user's second factor.
 */

import { useCallback, useEffect, useState } from "react";
import * as api from "./api";
import { Empty, Failure, Loading, toMessage } from "./Feedback";
import { useAccessMessages } from "./useMessages";

type State =
  | { readonly kind: "loading" }
  | { readonly kind: "ready"; readonly sessions: readonly api.SessionRecord[] }
  | { readonly kind: "failed"; readonly messageKey: string; readonly requestId: string | null };

export function SecuritySettingsPage() {
  const t = useAccessMessages();
  const [state, setState] = useState<State>({ kind: "loading" });

  const load = useCallback(async () => {
    try {
      const page = await api.listSessions();
      setState({ kind: "ready", sessions: page.items });
    } catch (error) {
      setState({ kind: "failed", ...toMessage(error) });
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  const revoke = async (sessionId: string) => {
    try {
      await api.revokeSession(sessionId);
      await load();
    } catch (error) {
      setState({ kind: "failed", ...toMessage(error) });
    }
  };

  if (state.kind === "loading") return <Loading />;
  if (state.kind === "failed") {
    return (
      <Failure
        messageKey={state.messageKey}
        requestId={state.requestId}
        onRetry={() => void load()}
      />
    );
  }

  const live = state.sessions.filter((row) => row.revoked_at === null);

  return (
    <section aria-labelledby="security-heading">
      <h2 id="security-heading">{t("access.security.title")}</h2>
      <h3>{t("access.sessions.title")}</h3>
      {live.length === 0 ? (
        <Empty />
      ) : (
        <ul data-testid="session-list">
          {live.map((row) => (
            <li key={row.id} data-testid="session-row">
              <span>{row.user_agent_family}</span>{" "}
              {row.is_current ? <strong>{t("access.sessions.current")}</strong> : null}{" "}
              <small>
                {t("access.sessions.lastSeen")}: {row.last_seen_at}
              </small>{" "}
              {row.is_current ? null : (
                <button type="button" onClick={() => void revoke(row.id)}>
                  {t("access.sessions.revoke")}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default SecuritySettingsPage;
