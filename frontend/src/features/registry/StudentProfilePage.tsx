/**
 * Single student profile from GET /api/v1/students/{id}.
 */

import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { getStudent, type StudentRecord } from "./api";
import { loadErrorKey } from "./loadErrorKey";

type LoadState =
  | { readonly status: "loading" }
  | { readonly status: "ready"; readonly student: StudentRecord }
  | { readonly status: "error"; readonly messageKey: string };

/** Student detail screen keyed by the :studentId route param. */
export function StudentProfilePage() {
  const { t } = useLanguage();
  const { studentId } = useParams<{ readonly studentId: string }>();
  const [state, setState] = useState<LoadState>({ status: "loading" });

  const load = useCallback(async (id: string) => {
    setState({ status: "loading" });
    try {
      const student = await getStudent(id);
      setState({ status: "ready", student });
    } catch (error) {
      setState({ status: "error", messageKey: loadErrorKey(error) });
    }
  }, []);

  useEffect(() => {
    if (studentId === undefined || studentId.length === 0) {
      setState({ status: "error", messageKey: "error.validation_failed" });
      return;
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load(studentId);
  }, [load, studentId]);

  return (
    <main>
      <p>
        <Link to="/registry/students">{t("registry.back_to_directory")}</Link>
      </p>
      <h1>{t("registry.student_profile_title")}</h1>
      {state.status === "loading" && <p role="status">{t("ui.loading")}</p>}
      {state.status === "error" && (
        <p role="alert">
          {t(state.messageKey)}{" "}
          {studentId !== undefined && studentId.length > 0 && (
            <button type="button" onClick={() => void load(studentId)}>
              {t("ui.retry")}
            </button>
          )}
        </p>
      )}
      {state.status === "ready" && (
        <>
          <p>{state.student.display_name}</p>
          <dl>
            <div>
              <dt>{t("registry.admission_no")}</dt>
              <dd>{state.student.admission_no}</dd>
            </div>
            <div>
              <dt>{t("registry.status")}</dt>
              <dd>{t(`registry.status.${state.student.status}`)}</dd>
            </div>
            <div>
              <dt>{t("registry.archived")}</dt>
              <dd>{String(state.student.archived)}</dd>
            </div>
            <div>
              <dt>{t("registry.date_of_birth")}</dt>
              <dd>{state.student.profile.date_of_birth ?? "—"}</dd>
            </div>
            <div>
              <dt>{t("registry.preferred_language")}</dt>
              <dd>{state.student.profile.preferred_language}</dd>
            </div>
          </dl>
          {state.student.external_ids.length > 0 && (
            <>
              <h2>{t("registry.external_ids")}</h2>
              <ul>
                {state.student.external_ids.map((externalId) => (
                  <li key={`${externalId.source}:${externalId.value}`}>
                    {externalId.source}: {externalId.value}
                  </li>
                ))}
              </ul>
            </>
          )}
        </>
      )}
    </main>
  );
}
