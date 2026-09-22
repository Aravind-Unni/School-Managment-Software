/**
 * The admission-register details form (address, blood group, parents ...),
 * shared by the Admit screen and the student profile.
 *
 * Controlled: the parent owns the values. Field problems from the server are
 * shown under the field they belong to. Choice lists match the server's
 * (GET /students/{id}/details returns the same lists).
 * Does not handle: saving (see ``saveStudentDetails``).
 */

import { request } from "@shared/api/client";
import { ApiError } from "@shared/api/errors";
import { useLanguage } from "@shared/i18n/LanguageContext";

export type StudentDetails = Record<string, string>;

export const BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"] as const;
const GENDERS = ["female", "male", "other"] as const;
const CATEGORIES = ["general", "obc", "sc", "st", "oec", "other"] as const;

type Field =
  | { readonly key: string; readonly kind: "text" | "date" | "tel" | "pin"; readonly wide?: boolean }
  | { readonly key: string; readonly kind: "choice"; readonly options: readonly string[]; readonly labelled?: boolean };

/** The form's groups, in the order an admission register reads. */
export const DETAIL_GROUPS: readonly { readonly title: string; readonly fields: readonly Field[] }[] = [
  {
    title: "details.group.personal",
    fields: [
      { key: "gender", kind: "choice", options: GENDERS, labelled: true },
      { key: "blood_group", kind: "choice", options: BLOOD_GROUPS },
      { key: "mother_tongue", kind: "text" },
      { key: "nationality", kind: "text" },
      { key: "religion", kind: "text" },
      { key: "category", kind: "choice", options: CATEGORIES, labelled: true },
      { key: "identification_marks", kind: "text", wide: true },
    ],
  },
  {
    title: "details.group.address",
    fields: [
      { key: "address_line", kind: "text", wide: true },
      { key: "place", kind: "text" },
      { key: "district", kind: "text" },
      { key: "state", kind: "text" },
      { key: "pin_code", kind: "pin" },
    ],
  },
  {
    title: "details.group.family",
    fields: [
      { key: "father_name", kind: "text" },
      { key: "father_occupation", kind: "text" },
      { key: "mother_name", kind: "text" },
      { key: "mother_occupation", kind: "text" },
    ],
  },
  {
    title: "details.group.schooling",
    fields: [
      { key: "admission_date", kind: "date" },
      { key: "previous_school", kind: "text" },
      { key: "tc_number", kind: "text" },
    ],
  },
  {
    title: "details.group.health",
    fields: [
      { key: "medical_notes", kind: "text", wide: true },
      { key: "emergency_contact_name", kind: "text" },
      { key: "emergency_contact_phone", kind: "tel" },
    ],
  },
];

/** Field-name → message key, from a 422 carrying ``details.<field>`` errors. */
export function detailProblems(error: unknown): Record<string, string> {
  if (!(error instanceof ApiError)) return {};
  const found: Record<string, string> = {};
  for (const item of error.fieldErrors ?? []) {
    if (item.field.startsWith("details.")) found[item.field.slice(8)] = item.message_key;
  }
  return found;
}

/** Load a pupil's details and the record version to save against. */
export function loadStudentDetails(
  studentId: string,
): Promise<{ readonly details: StudentDetails; readonly version: number }> {
  return request(`/api/v1/students/${studentId}/details`);
}

/** Replace a pupil's details (empty values are dropped by the server). */
export function saveStudentDetails(
  studentId: string,
  details: StudentDetails,
  expectedVersion: number,
): Promise<{ readonly details: StudentDetails; readonly version: number }> {
  return request(`/api/v1/students/${studentId}/details`, {
    method: "PUT",
    body: { details, expected_version: expectedVersion },
  });
}

export function StudentDetailsFields({
  value,
  onChange,
  problems = {},
}: {
  readonly value: StudentDetails;
  readonly onChange: (next: StudentDetails) => void;
  readonly problems?: Record<string, string>;
}) {
  const { t } = useLanguage();
  const set = (key: string, next: string) => onChange({ ...value, [key]: next });

  return (
    <>
      {DETAIL_GROUPS.map((group) => (
        <fieldset key={group.title} className="details-group">
          <legend>{t(group.title)}</legend>
          <div className="details-grid">
            {group.fields.map((field) => {
              const id = `detail-${field.key}`;
              const problem = problems[field.key];
              const current = value[field.key] ?? "";
              return (
                <label key={field.key} className={"wide" in field && field.wide ? "wide" : undefined}>
                  {t(`details.${field.key}`)}
                  {field.kind === "choice" ? (
                    <select id={id} value={current} onChange={(event) => set(field.key, event.target.value)}>
                      <option value="">—</option>
                      {field.options.map((option) => (
                        <option key={option} value={option}>
                          {field.labelled ? t(`details.${field.key}.${option}`) : option}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      id={id}
                      type={field.kind === "date" ? "date" : field.kind === "tel" ? "tel" : "text"}
                      inputMode={field.kind === "pin" ? "numeric" : undefined}
                      maxLength={field.kind === "pin" ? 6 : undefined}
                      value={current}
                      aria-invalid={problem ? true : undefined}
                      onChange={(event) => set(field.key, event.target.value)}
                    />
                  )}
                  {problem ? <span className="field-problem">{t(problem)}</span> : null}
                </label>
              );
            })}
          </div>
        </fieldset>
      ))}
    </>
  );
}

/** Read-only view of the details that are filled in, grouped like the form. */
export function StudentDetailsView({ value }: { readonly value: StudentDetails }) {
  const { t } = useLanguage();
  const groups = DETAIL_GROUPS.map((group) => ({
    ...group,
    fields: group.fields.filter((field) => (value[field.key] ?? "") !== ""),
  })).filter((group) => group.fields.length > 0);
  if (groups.length === 0) return <p className="hint">{t("details.none")}</p>;
  return (
    <div className="details-view">
      {groups.map((group) => (
        <section key={group.title}>
          <h4>{t(group.title)}</h4>
          <dl>
            {group.fields.map((field) => {
              const raw = value[field.key] ?? "";
              const shown = field.kind === "choice" && field.labelled ? t(`details.${field.key}.${raw}`) : raw;
              return (
                <div key={field.key}>
                  <dt>{t(`details.${field.key}`)}</dt>
                  <dd>{shown}</dd>
                </div>
              );
            })}
          </dl>
        </section>
      ))}
    </div>
  );
}
