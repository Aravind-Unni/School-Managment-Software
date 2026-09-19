/**
 * Role editor.
 *
 * Sends ``expected_version`` on every save, so a concurrent edit produces a visible
 * conflict rather than a silent overwrite. A 409 is surfaced with its own message,
 * because "reload and try again" is actionable while a generic failure is not.
 */

import { useCallback, useEffect, useState } from "react";
import { ApiError } from "@shared/api/errors";
import * as api from "./api";
import { Empty, Failure, Loading, toMessage } from "./Feedback";
import { useAccessMessages } from "./useMessages";

type State =
  | { readonly kind: "loading" }
  | { readonly kind: "ready"; readonly roles: readonly api.Role[] }
  | { readonly kind: "failed"; readonly messageKey: string; readonly requestId: string | null };

export function RoleEditorPage() {
  const t = useAccessMessages();
  const [state, setState] = useState<State>({ kind: "loading" });
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const page = await api.listRoles();
      setState({ kind: "ready", roles: page.items });
    } catch (error) {
      setState({ kind: "failed", ...toMessage(error) });
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  const save = async (role: api.Role) => {
    setNotice(null);
    try {
      await api.replaceGrants(role.id, {
        name: role.name,
        grants: role.grants,
        expectedVersion: role.version,
      });
      await load();
    } catch (error) {
      // A version conflict gets its own message: it is recoverable by reloading,
      // unlike a permission failure.
      if (error instanceof ApiError && error.code === "version_conflict") {
        setNotice("access.roles.conflict");
        return;
      }
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

  return (
    <section aria-labelledby="roles-heading">
      <h2 id="roles-heading">{t("access.roles.title")}</h2>
      {notice ? <p role="alert">{t(notice)}</p> : null}
      {state.roles.length === 0 ? (
        <Empty />
      ) : (
        <table>
          <caption>{t("access.roles.title")}</caption>
          <thead>
            <tr>
              <th scope="col">{t("access.roles.name")}</th>
              <th scope="col">{t("access.roles.grants")}</th>
              <th scope="col">{t("access.roles.version")}</th>
              <th scope="col" />
            </tr>
          </thead>
          <tbody>
            {state.roles.map((role) => (
              <tr key={role.id} data-testid="role-row">
                <th scope="row">
                  {role.name}
                  {role.is_owner_role ? ` (${t("access.roles.ownerRole")})` : ""}
                  {role.requires_two_factor ? ` — ${t("access.roles.requiresTwoFactor")}` : ""}
                </th>
                <td>{role.grants.map((grant) => grant.action).join(", ") || "—"}</td>
                <td>{role.version}</td>
                <td>
                  <button type="button" onClick={() => void save(role)}>
                    {t("access.roles.save")}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

export default RoleEditorPage;
