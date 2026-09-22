/**
 * One pupil's record: admission number, birth date, status and the
 * admission-register details (address, blood group, parents ...), which the
 * office can edit here.
 *
 * Does not handle: day-to-day information (attendance, marks, fees are on the
 * Student overview, linked from here) or parent records.
 */

import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { shortDate } from "@shared/format";
import { Problem } from "@shared/ui/Problem";
import { can, useSession } from "@app/SessionContext";
import { getStudent, type StudentRecord } from "./api";
import { StudentAvatar, StudentPhotoEditor } from "./StudentPhoto";
import {
  StudentDetailsFields,
  StudentDetailsView,
  detailProblems,
  loadStudentDetails,
  saveStudentDetails,
  type StudentDetails,
} from "./StudentDetailsFields";

export function StudentProfilePage() {
  const { t, language } = useLanguage();
  const { actions } = useSession();
  const canEdit = can(actions, "students.update");
  const { studentId = "" } = useParams<{ readonly studentId: string }>();
  const [student, setStudent] = useState<StudentRecord | null>(null);
  const [details, setDetails] = useState<StudentDetails>({});
  const [version, setVersion] = useState(0);
  const [draft, setDraft] = useState<StudentDetails | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [saved, setSaved] = useState(false);

  const load = useCallback(async () => {
    try {
      const [record, loaded] = await Promise.all([getStudent(studentId), loadStudentDetails(studentId)]);
      setStudent(record);
      setDetails(loaded.details);
      setVersion(loaded.version);
    } catch (caught) {
      setError(caught);
    }
  }, [studentId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loads this screen's data
    void load();
  }, [load]);

  const save = async () => {
    if (draft === null) return;
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      const result = await saveStudentDetails(studentId, draft, version);
      setDetails(result.details);
      setVersion(result.version);
      setDraft(null);
      setSaved(true);
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  };

  if (student === null) return error ? <Problem error={error} /> : <p role="status">{t("ui.loading")}</p>;

  return (
    <section aria-labelledby="profile-title" className="student-profile">
      <p>
        <Link to="/registry/students">{t("registry.back_to_directory")}</Link>
      </p>
      <div className="profile-head">
        {canEdit ? (
          <StudentPhotoEditor studentId={student.id} name={student.display_name} />
        ) : (
          <StudentAvatar studentId={student.id} name={student.display_name} size={112} />
        )}
        <h2 id="profile-title">{student.display_name}</h2>
      </div>
      <dl className="profile-facts">
        <div>
          <dt>{t("registry.admission_no")}</dt>
          <dd>{student.admission_no}</dd>
        </div>
        <div>
          <dt>{t("registry.date_of_birth")}</dt>
          <dd>{shortDate(student.profile.date_of_birth, language)}</dd>
        </div>
        <div>
          <dt>{t("registry.status")}</dt>
          <dd>{t(`registry.status.${student.status}`)}</dd>
        </div>
        <div>
          <dt>{t("registry.preferred_language")}</dt>
          <dd>{student.profile.preferred_language === "ml" ? "മലയാളം" : "English"}</dd>
        </div>
      </dl>
      <p>
        <Link className="button-link secondary" to={`/registry/overview?student=${student.id}`}>
          {t("details.open_overview")}
        </Link>
      </p>

      <div className="profile-heading">
        <h3>{t("details.title")}</h3>
        {canEdit && draft === null ? (
          <button
            type="button"
            className="secondary"
            onClick={() => {
              setDraft({ ...details });
              setSaved(false);
            }}
          >
            {t("details.edit")}
          </button>
        ) : null}
      </div>
      {saved ? (
        <p role="status" className="notice-success">
          {t("details.saved")}
        </p>
      ) : null}
      {draft === null ? (
        <StudentDetailsView value={details} />
      ) : (
        <form
          className="stack"
          onSubmit={(event) => {
            event.preventDefault();
            void save();
          }}
        >
          <StudentDetailsFields value={draft} onChange={setDraft} problems={detailProblems(error)} />
          <Problem error={error} />
          <div className="row-actions">
            <button type="submit" disabled={busy}>
              {busy ? t("ui.loading") : t("details.save")}
            </button>
            <button type="button" className="quiet" onClick={() => setDraft(null)}>
              {t("details.cancel")}
            </button>
          </div>
        </form>
      )}
    </section>
  );
}

export default StudentProfilePage;
