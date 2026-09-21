/**
 * Admit a student in one form: the parent (new, or an existing one for a
 * sibling), the student, their class for the current year, and optionally a
 * parent login.
 *
 * Steps run in order and each result is shown, so a failure part-way (say the
 * login name is taken) leaves the office knowing exactly what was saved.
 * Does not handle: bulk admission (use Import centre) or transfers.
 */

import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { Problem } from "@shared/ui/Problem";
import * as accessApi from "@features/access/api";
import * as api from "./api";
import { schoolToday, useSchoolStructure } from "./useSchoolStructure";

type ParentMode = "new" | "existing" | "none";

interface Outcome {
  readonly student: api.StudentRecord;
  readonly className: string | null;
  readonly parentName: string | null;
  readonly login: accessApi.ManagedAccount | null;
}

/** Pick the role parents get: the non-owner role whose name mentions guardian/parent. */
function parentRole(roles: readonly accessApi.Role[]): accessApi.Role | undefined {
  return roles.find((role) => !role.is_owner_role && /guardian|parent/i.test(role.name));
}

export function AdmitStudentPage() {
  const { t } = useLanguage();
  const { state } = useSchoolStructure();
  const [guardians, setGuardians] = useState<readonly api.Guardian[]>([]);
  const [roles, setRoles] = useState<readonly accessApi.Role[]>([]);

  const [admissionNo, setAdmissionNo] = useState("");
  const [studentName, setStudentName] = useState("");
  const [dateOfBirth, setDateOfBirth] = useState("");
  const [language, setLanguage] = useState<"en" | "ml">("en");
  const [sectionId, setSectionId] = useState("");
  const [parentMode, setParentMode] = useState<ParentMode>("new");
  const [parentName, setParentName] = useState("");
  const [parentPhone, setParentPhone] = useState("");
  const [parentEmail, setParentEmail] = useState("");
  const [existingGuardianId, setExistingGuardianId] = useState("");
  const [guardianFilter, setGuardianFilter] = useState("");
  const [createLogin, setCreateLogin] = useState(true);
  const [loginName, setLoginName] = useState("");

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [progress, setProgress] = useState<readonly string[]>([]);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  // Rows saved by an attempt that then failed part-way; a retry reuses them
  // rather than creating a second parent or a duplicate admission.
  const [savedGuardian, setSavedGuardian] = useState<api.Guardian | null>(null);
  const [savedStudent, setSavedStudent] = useState<api.StudentRecord | null>(null);
  const [savedEnrolment, setSavedEnrolment] = useState(false);

  useEffect(() => {
    api.listAllGuardians().then(setGuardians, () => setGuardians([]));
    // Roles need accounts/roles permission; without it the login option hides.
    accessApi.listAllRoles().then(setRoles, () => setRoles([]));
  }, []);

  const guardianRole = parentRole(roles);
  const filteredGuardians = useMemo(() => {
    const needle = guardianFilter.trim().toLowerCase();
    return guardians
      .filter((row) => !row.archived)
      .filter(
        (row) =>
          needle === "" ||
          row.display_name.toLowerCase().includes(needle) ||
          (row.phone ?? "").includes(needle),
      )
      .slice(0, 50);
  }, [guardians, guardianFilter]);

  if (state.kind === "loading") return <p role="status">{t("ui.loading")}</p>;
  if (state.kind === "failed") return <Problem error={state.error} />;
  const { year, sections } = state.structure;

  const reset = () => {
    setAdmissionNo("");
    setStudentName("");
    setDateOfBirth("");
    setParentName("");
    setParentPhone("");
    setParentEmail("");
    setExistingGuardianId("");
    setLoginName("");
    setProgress([]);
    setError(null);
    setOutcome(null);
    setSavedGuardian(null);
    setSavedStudent(null);
    setSavedEnrolment(false);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setOutcome(null);
    const done: string[] = [];
    const note = (line: string) => {
      done.push(line);
      setProgress([...done]);
    };
    try {
      const today = schoolToday();
      let guardian: api.Guardian | null = null;
      if (parentMode === "new" && savedGuardian !== null) {
        guardian = savedGuardian;
      } else if (parentMode === "new") {
        guardian = await api.createGuardian({
          displayName: parentName.trim(),
          phone: parentPhone.trim() || null,
          email: parentEmail.trim() || null,
        });
        setSavedGuardian(guardian);
        note(`${t("registry.admit.parent_saved")}: ${guardian.display_name}`);
      } else if (parentMode === "existing") {
        guardian = guardians.find((row) => row.id === existingGuardianId) ?? null;
      }
      const fromDate = year !== null && year.start > today ? year.start : today;
      let student = savedStudent;
      if (student === null) {
        student = await api.createStudent({
          admissionNo: admissionNo.trim(),
          displayName: studentName.trim(),
          dateOfBirth: dateOfBirth || null,
          preferredLanguage: language,
          guardianLinks: guardian ? [{ guardianId: guardian.id, fromDate }] : [],
        });
        setSavedStudent(student);
        note(`${t("registry.admit.student_saved")}: ${student.display_name}`);
      }
      let className: string | null = null;
      if (sectionId && year !== null && savedEnrolment) {
        className = sections.find((row) => row.id === sectionId)?.label ?? null;
      } else if (sectionId && year !== null) {
        await api.createEnrolment({
          studentId: student.id,
          yearId: year.id,
          sectionId,
          fromDate,
        });
        setSavedEnrolment(true);
        className = sections.find((row) => row.id === sectionId)?.label ?? null;
        note(`${t("registry.admit.class_saved")}: ${className ?? ""}`);
      }
      let login: accessApi.ManagedAccount | null = null;
      if (guardian && parentMode === "new" && createLogin && guardianRole) {
        login = await accessApi.createAccount({
          loginName: loginName.trim() || accessApi.suggestLoginName(guardian.display_name),
          displayName: guardian.display_name,
          personId: guardian.id,
          roleIds: [guardianRole.id],
        });
        note(`${t("registry.admit.login_saved")}: ${login.login_name}`);
      }
      setOutcome({ student, className, parentName: guardian?.display_name ?? null, login });
      if (guardian && parentMode === "new") setGuardians((rows) => [...rows, guardian]);
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  };

  if (outcome !== null) {
    return (
      <section aria-labelledby="admit-done">
        <h2 id="admit-done">{t("registry.admit.done_title")}</h2>
        <ul>
          {progress.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
        {outcome.login?.temporary_password ? (
          <div className="credential-slip" data-testid="credential-slip">
            <p>{t("registry.admit.slip_intro")}</p>
            <dl>
              <dt>{t("access.login.name")}</dt>
              <dd>
                <code>{outcome.login.login_name}</code>
              </dd>
              <dt>{t("registry.admit.temporary_password")}</dt>
              <dd>
                <code data-testid="temporary-password">{outcome.login.temporary_password}</code>
              </dd>
            </dl>
            <p>
              <small>{t("registry.admit.slip_warning")}</small>
            </p>
            <button type="button" className="secondary" onClick={() => window.print()}>
              {t("registry.admit.print")}
            </button>
          </div>
        ) : null}
        <p>
          <Link to={`/registry/students/${outcome.student.id}`}>
            {t("registry.open_profile")}
          </Link>
        </p>
        <button type="button" onClick={reset}>
          {t("registry.admit.another")}
        </button>
      </section>
    );
  }

  return (
    <section aria-labelledby="admit-title">
      <h2 id="admit-title">{t("registry.admit.title")}</h2>
      <p>
        {t("registry.admit.year")}: <strong>{year?.name ?? "—"}</strong>
      </p>
      <form onSubmit={(event) => void submit(event)} className="stack">
        <fieldset>
          <legend>{t("registry.admit.student")}</legend>
          <label>
            {t("registry.admission_no")}
            <input required value={admissionNo} onChange={(e) => setAdmissionNo(e.target.value)} />
          </label>
          <label>
            {t("registry.admit.full_name")}
            <input required value={studentName} onChange={(e) => setStudentName(e.target.value)} />
          </label>
          <label>
            {t("registry.date_of_birth")}
            <input type="date" value={dateOfBirth} onChange={(e) => setDateOfBirth(e.target.value)} />
          </label>
          <label>
            {t("registry.preferred_language")}
            <select value={language} onChange={(e) => setLanguage(e.target.value as "en" | "ml")}>
              <option value="en">English</option>
              <option value="ml">മലയാളം</option>
            </select>
          </label>
          <label>
            {t("registry.admit.class")}
            <select value={sectionId} onChange={(e) => setSectionId(e.target.value)} required>
              <option value="">{t("registry.admit.choose_class")}</option>
              {sections.map((section) => (
                <option key={section.id} value={section.id}>
                  {section.label}
                </option>
              ))}
            </select>
          </label>
        </fieldset>

        <fieldset>
          <legend>{t("registry.admit.parent")}</legend>
          <div role="radiogroup" className="inline-options">
            {(["new", "existing", "none"] as const).map((mode) => (
              <label key={mode} className="inline">
                <input
                  type="radio"
                  name="parent-mode"
                  checked={parentMode === mode}
                  onChange={() => setParentMode(mode)}
                />
                {t(`registry.admit.parent_${mode}`)}
              </label>
            ))}
          </div>
          {parentMode === "new" ? (
            <>
              <label>
                {t("registry.admit.parent_name")}
                <input required value={parentName} onChange={(e) => setParentName(e.target.value)} />
              </label>
              <label>
                {t("registry.admit.phone")}
                <input type="tel" value={parentPhone} onChange={(e) => setParentPhone(e.target.value)} />
              </label>
              <label>
                {t("registry.admit.email")} ({t("ui.optional")})
                <input type="email" value={parentEmail} onChange={(e) => setParentEmail(e.target.value)} />
              </label>
              {guardianRole ? (
                <>
                  <label className="inline">
                    <input
                      type="checkbox"
                      checked={createLogin}
                      onChange={(e) => setCreateLogin(e.target.checked)}
                    />
                    {t("registry.admit.create_login")}
                  </label>
                  {createLogin ? (
                    <label>
                      {t("access.login.name")}
                      <input
                        value={loginName}
                        placeholder={accessApi.suggestLoginName(parentName) || "parent.name"}
                        onChange={(e) => setLoginName(e.target.value)}
                      />
                    </label>
                  ) : null}
                </>
              ) : null}
            </>
          ) : null}
          {parentMode === "existing" ? (
            <>
              <label>
                {t("registry.admit.find_parent")}
                <input value={guardianFilter} onChange={(e) => setGuardianFilter(e.target.value)} />
              </label>
              <label>
                {t("registry.admit.parent")}
                <select
                  required
                  value={existingGuardianId}
                  onChange={(e) => setExistingGuardianId(e.target.value)}
                >
                  <option value="">—</option>
                  {filteredGuardians.map((row) => (
                    <option key={row.id} value={row.id}>
                      {row.display_name}
                      {row.phone ? ` (${row.phone})` : ""}
                    </option>
                  ))}
                </select>
              </label>
            </>
          ) : null}
        </fieldset>

        {progress.length > 0 ? (
          <ul aria-label={t("registry.admit.saved_so_far")}>
            {progress.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        ) : null}
        <Problem error={error} />
        <button type="submit" disabled={busy}>
          {busy ? t("ui.loading") : t("registry.admit.submit")}
        </button>
      </form>
    </section>
  );
}

export default AdmitStudentPage;
