/**
 * Which pupil a page is about. Parents and pupils get their own children as
 * tabs (the first chosen straight away); staff search for any pupil they may
 * see. ``?student=<id>`` in the address opens on that pupil, so other pages
 * can link straight here.
 *
 * Does not handle: loading the page's own data (the page does that for the
 * pupil this returns).
 */

import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { Loading } from "@shared/ui/Loading";
import * as api from "./api";
import { StudentPicker, type PickedStudent } from "./StudentPicker";

export function usePupilChoice() {
  const [params] = useSearchParams();
  const linked = params.get("student");
  const [mine, setMine] = useState<readonly api.MyStudent[] | null>(null);
  const [chosen, setChosen] = useState<PickedStudent | null>(null);

  useEffect(() => {
    api.listMyStudents().then(
      (rows) => {
        setMine(rows);
        const found = rows.find((row) => row.id === linked) ?? rows[0];
        if (found) setChosen(found);
        else if (linked) {
          api.getStudent(linked).then(
            (row) => setChosen({ id: row.id, display_name: row.display_name, admission_no: row.admission_no }),
            () => undefined,
          );
        }
      },
      () => setMine([]),
    );
  }, [linked]);

  return { mine, chosen, setChosen };
}

export function PupilChooser({
  mine,
  chosen,
  onChoose,
}: {
  readonly mine: readonly api.MyStudent[] | null;
  readonly chosen: PickedStudent | null;
  readonly onChoose: (row: PickedStudent | null) => void;
}) {
  const { t } = useLanguage();
  if (mine === null) return <Loading />;
  if (mine.length > 0) {
    return mine.length > 1 ? (
      <div className="child-switcher" role="tablist" aria-label={t("overview.children")}>
        {mine.map((row) => (
          <button
            key={row.id}
            type="button"
            role="tab"
            aria-selected={chosen?.id === row.id}
            className={chosen?.id === row.id ? "" : "secondary"}
            onClick={() => onChoose(row)}
          >
            {row.display_name}
          </button>
        ))}
      </div>
    ) : null;
  }
  return chosen === null ? (
    <StudentPicker onPick={onChoose} />
  ) : (
    <div className="picked-person">
      <strong>{chosen.display_name}</strong>
      <span className="hint">{chosen.admission_no}</span>
      <button type="button" className="quiet" onClick={() => onChoose(null)}>
        {t("fees.collect.change_student")}
      </button>
    </div>
  );
}
