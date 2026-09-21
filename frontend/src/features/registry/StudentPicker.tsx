/**
 * Find a student by typing part of a name or admission number.
 *
 * Shows up to 20 matches as a list of buttons: works the same with a mouse,
 * a keyboard and a thumb. Does not handle: filtering by class (search does).
 */

import { useEffect, useState } from "react";
import { useLanguage } from "@shared/i18n/LanguageContext";
import * as api from "./api";

export interface PickedStudent {
  readonly id: string;
  readonly display_name: string;
  readonly admission_no: string;
}

export function StudentPicker({
  onPick,
  label,
}: {
  readonly onPick: (student: PickedStudent) => void;
  readonly label?: string;
}) {
  const { t } = useLanguage();
  const [query, setQuery] = useState("");
  const [matches, setMatches] = useState<readonly api.StudentRecord[]>([]);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    const needle = query.trim();
    if (needle.length < 2) {
      setMatches([]);
      return undefined;
    }
    let cancelled = false;
    const timer = window.setTimeout(() => {
      setSearching(true);
      api.searchStudents(needle).then(
        (rows) => {
          if (!cancelled) setMatches(rows);
        },
        () => {
          if (!cancelled) setMatches([]);
        },
      ).finally(() => {
        if (!cancelled) setSearching(false);
      });
    }, 250);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [query]);

  return (
    <div className="student-picker">
      <label>
        {label ?? t("picker.find_student")}
        <input
          type="search"
          value={query}
          placeholder={t("picker.placeholder")}
          onChange={(event) => setQuery(event.target.value)}
          autoComplete="off"
        />
      </label>
      {searching ? <p className="hint">{t("ui.loading")}</p> : null}
      {matches.length > 0 ? (
        <ul className="picker-results">
          {matches.map((row) => (
            <li key={row.id}>
              <button
                type="button"
                className="secondary"
                onClick={() => {
                  onPick(row);
                  setQuery("");
                  setMatches([]);
                }}
              >
                <strong>{row.display_name}</strong>
                <span className="hint">{row.admission_no}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : query.trim().length >= 2 && !searching ? (
        <p className="hint">{t("picker.no_match")}</p>
      ) : null}
    </div>
  );
}
