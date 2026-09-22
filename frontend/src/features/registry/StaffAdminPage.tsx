/**
 * Staff administration: add a staff member (with an optional login and role),
 * and assign teachers to teach a subject to a class.
 *
 * A teaching assignment is what lets a teacher mark attendance and enter marks
 * for that class; without one, a teacher sees nothing to do.
 * Does not handle: ending an assignment (edit it from the class page later) or
 * payroll-style staff records.
 */

import { useEffect, useState, type FormEvent } from "react";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { Problem } from "@shared/ui/Problem";
import * as accessApi from "@features/access/api";
import * as api from "./api";
import { schoolToday, useSchoolStructure } from "./useSchoolStructure";
import { Loading } from "@shared/ui/Loading";

function AddStaffForm({
  roles,
  onAdded,
}: {
  readonly roles: readonly accessApi.Role[];
  readonly onAdded: (staff: api.StaffMember) => void;
}) {
  const { t } = useLanguage();
  // People-facing staff roles only: not owner, family roles or the jobs account's role.
  const staffRoles = roles.filter(
    (role) => !role.is_owner_role && !/guardian|parent|student|automatic jobs/i.test(role.name),
  );
  const [name, setName] = useState("");
  const [roleId, setRoleId] = useState("");
  const [loginName, setLoginName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [created, setCreated] = useState<{
    staff: api.StaffMember;
    login: accessApi.ManagedAccount | null;
  } | null>(null);

  useEffect(() => {
    if (roleId === "" && staffRoles.length > 0) {
      const teacher = staffRoles.find((role) => /teacher/i.test(role.name)) ?? staffRoles[0];
      // eslint-disable-next-line react-hooks/set-state-in-effect -- loads this screen's data
      if (teacher) setRoleId(teacher.id);
    }
  }, [roleId, staffRoles]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const staff = created?.staff ?? (await api.createStaff({ displayName: name.trim() }));
      setCreated({ staff, login: null });
      onAdded(staff);
      let login: accessApi.ManagedAccount | null = null;
      if (roleId !== "") {
        login = await accessApi.createAccount({
          loginName: loginName.trim() || accessApi.suggestLoginName(staff.display_name),
          displayName: staff.display_name,
          personId: staff.id,
          roleIds: [roleId],
        });
      }
      setCreated({ staff, login });
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  };

  if (created !== null && error === null && !busy) {
    return (
      <div>
        <p role="status">
          {t("registry.staff.added")}: <strong>{created.staff.display_name}</strong>
        </p>
        {created.login?.temporary_password ? (
          <div className="credential-slip" data-testid="credential-slip">
            <dl>
              <dt>{t("access.login.name")}</dt>
              <dd>
                <code>{created.login.login_name}</code>
              </dd>
              <dt>{t("registry.admit.temporary_password")}</dt>
              <dd>
                <code data-testid="temporary-password">{created.login.temporary_password}</code>
              </dd>
            </dl>
            <p>
              <small>{t("registry.admit.slip_warning")}</small>
            </p>
          </div>
        ) : null}
        <button
          type="button"
          onClick={() => {
            setCreated(null);
            setName("");
            setLoginName("");
          }}
        >
          {t("registry.staff.add_another")}
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={(event) => void submit(event)} className="stack">
      <label>
        {t("registry.admit.full_name")}
        <input required value={name} onChange={(e) => setName(e.target.value)} />
      </label>
      <label>
        {t("registry.staff.role")}
        <select value={roleId} onChange={(e) => setRoleId(e.target.value)}>
          <option value="">{t("registry.staff.no_login")}</option>
          {staffRoles.map((role) => (
            <option key={role.id} value={role.id}>
              {role.name}
            </option>
          ))}
        </select>
      </label>
      {roleId !== "" ? (
        <label>
          {t("access.login.name")}
          <input
            value={loginName}
            placeholder={accessApi.suggestLoginName(name) || "first.last"}
            onChange={(e) => setLoginName(e.target.value)}
          />
        </label>
      ) : null}
      <Problem error={error} />
      <button aria-busy={busy} type="submit" disabled={busy}>
        {busy ? t("ui.loading") : t("registry.staff.add")}
      </button>
    </form>
  );
}

function AssignTeachingForm({ staff }: { readonly staff: readonly api.StaffMember[] }) {
  const { t } = useLanguage();
  const { state } = useSchoolStructure();
  const [staffId, setStaffId] = useState("");
  const [sectionIds, setSectionIds] = useState<readonly string[]>([]);
  const [subjectId, setSubjectId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [done, setDone] = useState<readonly string[]>([]);

  if (state.kind === "loading") return <Loading />;
  if (state.kind === "failed") return <Problem error={state.error} />;
  const { sections, subjects, year } = state.structure;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    const lines: string[] = [];
    try {
      const today = schoolToday();
      const fromDate = year !== null && year.start > today ? year.start : today;
      for (const sectionId of sectionIds) {
        await api.createTeachingAssignment({ staffId, sectionId, subjectId, fromDate });
        const teacher = staff.find((row) => row.id === staffId)?.display_name ?? "";
        const section = sections.find((row) => row.id === sectionId)?.label ?? "";
        const subject = subjects.find((row) => row.id === subjectId)?.display_name ?? "";
        lines.push(`${teacher} → ${subject}, ${section}`);
        setDone([...lines]);
      }
      setSectionIds([]);
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={(event) => void submit(event)} className="stack">
      <label>
        {t("registry.staff.teacher")}
        <select required value={staffId} onChange={(e) => setStaffId(e.target.value)}>
          <option value="">—</option>
          {staff
            .filter((row) => !row.archived)
            .map((row) => (
              <option key={row.id} value={row.id}>
                {row.display_name}
              </option>
            ))}
        </select>
      </label>
      <label>
        {t("registry.staff.subject")}
        <select required value={subjectId} onChange={(e) => setSubjectId(e.target.value)}>
          <option value="">—</option>
          {subjects.map((row) => (
            <option key={row.id} value={row.id}>
              {row.display_name}
            </option>
          ))}
        </select>
      </label>
      <label>
        {t("registry.staff.classes")}
        <select
          multiple
          required
          size={Math.min(10, Math.max(4, sections.length))}
          value={[...sectionIds]}
          onChange={(e) =>
            setSectionIds(Array.from(e.target.selectedOptions).map((option) => option.value))
          }
        >
          {sections.map((row) => (
            <option key={row.id} value={row.id}>
              {row.label}
            </option>
          ))}
        </select>
      </label>
      <p>
        <small>{t("registry.staff.classes_help")}</small>
      </p>
      {done.length > 0 ? (
        <ul aria-label={t("registry.staff.assigned")}>
          {done.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      ) : null}
      <Problem error={error} />
      <button aria-busy={busy} type="submit" disabled={busy || sectionIds.length === 0}>
        {busy ? t("ui.loading") : t("registry.staff.assign")}
      </button>
    </form>
  );
}

export function StaffAdminPage() {
  const { t } = useLanguage();
  const [staff, setStaff] = useState<readonly api.StaffMember[]>([]);
  const [roles, setRoles] = useState<readonly accessApi.Role[]>([]);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    api.listAllStaff().then(setStaff, setError);
    accessApi.listAllRoles().then(setRoles, () => setRoles([]));
  }, []);

  return (
    <section aria-labelledby="staff-title">
      <h2 id="staff-title">{t("registry.staff.title")}</h2>
      <Problem error={error} />
      <div className="two-column">
        <div>
          <h3>{t("registry.staff.add_title")}</h3>
          <AddStaffForm roles={roles} onAdded={(row) => setStaff((rows) => [...rows, row])} />
        </div>
        <div>
          <h3>{t("registry.staff.assign_title")}</h3>
          <AssignTeachingForm staff={staff} />
        </div>
      </div>
      <h3>{t("registry.staff.list_title")}</h3>
      {staff.length === 0 ? (
        <p role="status">{t("ui.empty")}</p>
      ) : (
        <ul className="plain-list">
          {staff.map((row) => (
            <li key={row.id}>{row.display_name}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default StaffAdminPage;
