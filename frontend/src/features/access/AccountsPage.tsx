/**
 * Account administration: every login in the school, with roles, 2FA state,
 * and the actions an office needs: change roles, reset a forgotten password,
 * deactivate someone who has left.
 *
 * Logins for students, parents and staff are normally created from the
 * admission and staff pages, which link them to the right person; this page
 * can also create an unlinked login (e.g. a second administrator).
 * Every action here needs a recent second factor; the server enforces it.
 */

import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { Problem } from "@shared/ui/Problem";
import * as api from "./api";

interface Slip {
  readonly loginName: string;
  readonly password: string;
}

function CredentialSlip({ slip, onClose }: { readonly slip: Slip; readonly onClose: () => void }) {
  const { t } = useLanguage();
  return (
    <div className="credential-slip" data-testid="credential-slip" role="status">
      <dl>
        <dt>{t("access.login.name")}</dt>
        <dd>
          <code>{slip.loginName}</code>
        </dd>
        <dt>{t("registry.admit.temporary_password")}</dt>
        <dd>
          <code data-testid="temporary-password">{slip.password}</code>
        </dd>
      </dl>
      <p>
        <small>{t("registry.admit.slip_warning")}</small>
      </p>
      <button type="button" className="secondary" onClick={() => window.print()}>
        {t("registry.admit.print")}
      </button>{" "}
      <button type="button" onClick={onClose}>
        {t("access.accounts.done")}
      </button>
    </div>
  );
}

function RoleChooser({
  roles,
  selected,
  onChange,
}: {
  readonly roles: readonly api.Role[];
  readonly selected: readonly string[];
  readonly onChange: (next: readonly string[]) => void;
}) {
  return (
    <div className="inline-options">
      {roles.map((role) => (
        <label key={role.id} className="inline">
          <input
            type="checkbox"
            checked={selected.includes(role.id)}
            onChange={(event) =>
              onChange(
                event.target.checked
                  ? [...selected, role.id]
                  : selected.filter((id) => id !== role.id),
              )
            }
          />
          {role.name}
        </label>
      ))}
    </div>
  );
}

export function AccountsPage() {
  const { t } = useLanguage();
  const [accounts, setAccounts] = useState<readonly api.Account[]>([]);
  const [roles, setRoles] = useState<readonly api.Role[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [filter, setFilter] = useState("");
  const [editing, setEditing] = useState<string | null>(null);
  const [editRoles, setEditRoles] = useState<readonly string[]>([]);
  const [slip, setSlip] = useState<Slip | null>(null);
  const [newName, setNewName] = useState("");
  const [newLogin, setNewLogin] = useState("");
  const [newRoles, setNewRoles] = useState<readonly string[]>([]);

  const load = useCallback(async () => {
    try {
      const collected: api.Account[] = [];
      let cursor: string | undefined;
      do {
        const page = await api.listAccounts(cursor);
        collected.push(...page.items);
        cursor = page.next_cursor ?? undefined;
      } while (cursor !== undefined);
      setAccounts(collected);
      setRoles(await api.listAllRoles());
      setError(null);
    } catch (caught) {
      setError(caught);
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const roleName = useMemo(() => new Map(roles.map((role) => [role.id, role.name])), [roles]);
  // The automatic-jobs account cannot sign in and is not a person; hide it.
  const visible = accounts.filter((row) => row.login_name !== "system.jobs").filter((row) => {
    const needle = filter.trim().toLowerCase();
    return (
      needle === "" ||
      row.display_name.toLowerCase().includes(needle) ||
      row.login_name.toLowerCase().includes(needle)
    );
  });

  const act = async (work: () => Promise<void>) => {
    setError(null);
    try {
      await work();
      await load();
    } catch (caught) {
      setError(caught);
    }
  };

  const create = (event: FormEvent) => {
    event.preventDefault();
    void act(async () => {
      const created = await api.createAccount({
        loginName: newLogin.trim() || api.suggestLoginName(newName),
        displayName: newName.trim(),
        personId: null,
        roleIds: newRoles,
      });
      if (created.temporary_password) {
        setSlip({ loginName: created.login_name, password: created.temporary_password });
      }
      setNewName("");
      setNewLogin("");
      setNewRoles([]);
    });
  };

  if (!loaded) return <p role="status">{t("ui.loading")}</p>;

  return (
    <section aria-labelledby="accounts-title">
      <h2 id="accounts-title">{t("access.accounts.title")}</h2>
      <p>{t("access.accounts.intro")}</p>
      <Problem error={error} />
      {slip !== null ? <CredentialSlip slip={slip} onClose={() => setSlip(null)} /> : null}

      <label>
        {t("access.accounts.search")}
        <input value={filter} onChange={(event) => setFilter(event.target.value)} />
      </label>
      <div className="table-scroll">
        <table className="data">
          <thead>
            <tr>
              <th scope="col">{t("access.accounts.name")}</th>
              <th scope="col">{t("access.login.name")}</th>
              <th scope="col">{t("access.accounts.roles")}</th>
              <th scope="col">{t("access.accounts.status")}</th>
              <th scope="col" />
            </tr>
          </thead>
          <tbody>
            {visible.map((account) => (
              <tr key={account.id} data-testid="account-row">
                <th scope="row">{account.display_name}</th>
                <td>
                  <code>{account.login_name}</code>
                </td>
                <td>
                  {editing === account.id ? (
                    <RoleChooser roles={roles} selected={editRoles} onChange={setEditRoles} />
                  ) : (
                    account.role_ids.map((id) => roleName.get(id) ?? "?").join(", ") || "—"
                  )}
                </td>
                <td>
                  {account.active ? t("access.accounts.active") : t("access.accounts.inactive")}
                  {account.two_factor_required && !account.has_active_factor
                    ? ` · ${t("access.accounts.no_2fa_yet")}`
                    : ""}
                </td>
                <td className="row-actions">
                  {editing === account.id ? (
                    <>
                      <button
                        type="button"
                        onClick={() =>
                          void act(async () => {
                            await api.replaceAccountRoles(account.id, {
                              roleIds: editRoles,
                              expectedVersion: account.version,
                            });
                            setEditing(null);
                          })
                        }
                      >
                        {t("access.roles.save")}
                      </button>
                      <button type="button" className="secondary" onClick={() => setEditing(null)}>
                        {t("ui.cancel")}
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        type="button"
                        className="secondary"
                        onClick={() => {
                          setEditing(account.id);
                          setEditRoles(account.role_ids);
                        }}
                      >
                        {t("access.accounts.change_roles")}
                      </button>
                      <button
                        type="button"
                        className="secondary"
                        onClick={() =>
                          void act(async () => {
                            const reset = await api.resetAccountPassword(account.id);
                            if (reset.temporary_password) {
                              setSlip({
                                loginName: reset.login_name,
                                password: reset.temporary_password,
                              });
                            }
                          })
                        }
                      >
                        {t("access.accounts.reset_password")}
                      </button>
                      <button
                        type="button"
                        className="secondary"
                        onClick={() =>
                          void act(async () => {
                            await api.setAccountActive(account.id, {
                              active: !account.active,
                              expectedVersion: account.version,
                            });
                          })
                        }
                      >
                        {account.active
                          ? t("access.accounts.deactivate")
                          : t("access.accounts.activate")}
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3>{t("access.accounts.create_title")}</h3>
      <p>
        <small>{t("access.accounts.create_help")}</small>
      </p>
      <form onSubmit={create} className="stack">
        <label>
          {t("access.accounts.name")}
          <input required value={newName} onChange={(event) => setNewName(event.target.value)} />
        </label>
        <label>
          {t("access.login.name")}
          <input
            value={newLogin}
            placeholder={api.suggestLoginName(newName) || "first.last"}
            onChange={(event) => setNewLogin(event.target.value)}
          />
        </label>
        <fieldset>
          <legend>{t("access.accounts.roles")}</legend>
          <RoleChooser roles={roles} selected={newRoles} onChange={setNewRoles} />
        </fieldset>
        <button type="submit">{t("access.accounts.create")}</button>
      </form>
    </section>
  );
}

export default AccountsPage;
