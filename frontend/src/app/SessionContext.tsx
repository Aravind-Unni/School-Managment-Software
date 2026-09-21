/**
 * Session bootstrap for the product shell.
 *
 * Loads the current session and the caller's held action codes so navigation can
 * hide links the backend would refuse. Never trusts a client-asserted role.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import * as accessApi from "@features/access/api";
import type { Authenticated } from "@features/access/api";

interface SessionState {
  readonly status: "loading" | "anonymous" | "authenticated";
  readonly session: Authenticated | null;
  readonly actions: ReadonlySet<string>;
  readonly refresh: () => Promise<void>;
  readonly signOut: () => Promise<void>;
}

const SessionContext = createContext<SessionState | null>(null);

/** Provide session state to the shell and pages. */
export function SessionProvider({ children }: { readonly children: ReactNode }) {
  const [status, setStatus] = useState<SessionState["status"]>("loading");
  const [session, setSession] = useState<Authenticated | null>(null);
  const [actions, setActions] = useState<ReadonlySet<string>>(new Set());

  const refresh = useCallback(async () => {
    try {
      const current = await accessApi.currentSession();
      setSession(current);
      try {
        const caps = await accessApi.listCapabilities();
        setActions(new Set(caps.actions));
      } catch {
        setActions(new Set());
      }
      setStatus("authenticated");
    } catch {
      setSession(null);
      setActions(new Set());
      setStatus("anonymous");
    }
  }, []);

  const signOut = useCallback(async () => {
    try {
      await accessApi.logout();
    } finally {
      setSession(null);
      setActions(new Set());
      setStatus("anonymous");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <SessionContext.Provider value={{ status, session, actions, refresh, signOut }}>
      {children}
    </SessionContext.Provider>
  );
}

/** Read session state. Throws if used outside SessionProvider. */
export function useSession(): SessionState {
  const value = useContext(SessionContext);
  if (value === null) {
    throw new Error("useSession requires SessionProvider");
  }
  return value;
}

/** True when the caller holds the action, or when no action is required. */
export function can(actions: ReadonlySet<string>, permission: string | undefined): boolean {
  if (permission === undefined || permission === "") {
    return true;
  }
  return actions.has(permission);
}
