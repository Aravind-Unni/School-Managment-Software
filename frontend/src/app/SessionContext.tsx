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
import type { Authenticated as AuthenticatedBase } from "@features/access/api";

/** The session plus the header niceties /auth/session also returns. */
type Authenticated = AuthenticatedBase & {
  readonly display_name?: string;
  readonly login_name?: string;
  readonly school_name?: string | null;
};

export interface SessionState {
  readonly status: "loading" | "anonymous" | "authenticated";
  readonly session: Authenticated | null;
  readonly actions: ReadonlySet<string>;
  /** Actions held only for oneself or one's own child (pupils and parents). */
  readonly selfOnly: ReadonlySet<string>;
  readonly refresh: () => Promise<void>;
  readonly signOut: () => Promise<void>;
}

/** Exported so tests can supply a fixed session without network bootstrap. */
export const SessionContext = createContext<SessionState | null>(null);

/** Provide session state to the shell and pages. */
export function SessionProvider({ children }: { readonly children: ReactNode }) {
  const [status, setStatus] = useState<SessionState["status"]>("loading");
  const [session, setSession] = useState<Authenticated | null>(null);
  const [actions, setActions] = useState<ReadonlySet<string>>(new Set());
  const [selfOnly, setSelfOnly] = useState<ReadonlySet<string>>(new Set());

  const refresh = useCallback(async () => {
    try {
      const current = await accessApi.currentSession();
      setSession(current);
      try {
        const caps = await accessApi.listCapabilities();
        setActions(new Set(caps.actions));
        setSelfOnly(new Set(caps.self_only_actions ?? []));
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
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loads this screen's data
    void refresh();
  }, [refresh]);

  return (
    <SessionContext.Provider value={{ status, session, actions, selfOnly, refresh, signOut }}>
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

/**
 * True when this account can actually use a page: it holds the action, and
 * if it holds it only for itself or its own child, the page is one built for
 * families. Hides staff tools from parents rather than letting them refuse.
 */
export function canUseRoute(
  actions: ReadonlySet<string>,
  selfOnly: ReadonlySet<string>,
  route: { readonly requiredPermission?: string; readonly forFamilies?: boolean },
): boolean {
  if (!can(actions, route.requiredPermission)) return false;
  if (route.requiredPermission && selfOnly.has(route.requiredPermission)) return route.forFamilies === true;
  return true;
}
