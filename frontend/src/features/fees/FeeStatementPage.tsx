/**
 * A student's fee statement: what is left to pay and every charge and
 * payment. Parents see their own child; office staff search for a student.
 */

import { useEffect, useState } from "react";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { listMyStudents, type MyStudent } from "@features/registry/api";
import { FeesPanel } from "@features/registry/StudentOverviewPage";
import { StudentPicker, type PickedStudent } from "@features/registry/StudentPicker";

export function FeeStatementPage() {
  const { t } = useLanguage();
  const [mine, setMine] = useState<readonly MyStudent[] | null>(null);
  const [student, setStudent] = useState<PickedStudent | null>(null);

  useEffect(() => {
    listMyStudents().then(
      (rows) => {
        setMine(rows);
        if (rows[0]) setStudent(rows[0]);
      },
      () => setMine([]),
    );
  }, []);

  if (mine === null) return <p role="status">{t("ui.loading")}</p>;
  return (
    <section aria-labelledby="statement-title">
      <h2 id="statement-title">{t("fees.statement_title")}</h2>
      {mine.length > 1 ? (
        <div className="child-switcher">
          {mine.map((row) => (
            <button
              key={row.id}
              type="button"
              className={student?.id === row.id ? "" : "secondary"}
              onClick={() => setStudent(row)}
            >
              {row.display_name}
            </button>
          ))}
        </div>
      ) : null}
      {mine.length === 0 ? <StudentPicker onPick={setStudent} /> : null}
      {student ? (
        <>
          <p>
            <strong>{student.display_name}</strong> <span className="hint">{student.admission_no}</span>
          </p>
          <div className="overview-grid" key={student.id}>
            <FeesPanel student={student} />
          </div>
        </>
      ) : null}
    </section>
  );
}
