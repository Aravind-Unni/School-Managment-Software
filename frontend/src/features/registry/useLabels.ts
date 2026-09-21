/**
 * Human labels for ids a screen already has: sections ("Std 6 – A") and
 * staff names. Loads once; falls back to a short id while loading or when the
 * viewer may not read the list.
 */

import { useEffect, useState } from "react";
import * as api from "./api";
import { useSchoolStructure } from "./useSchoolStructure";

export function useLabels() {
  const { state } = useSchoolStructure();
  const [staff, setStaff] = useState<ReadonlyMap<string, string>>(new Map());
  useEffect(() => {
    api.listAllStaff().then(
      (rows) => setStaff(new Map(rows.map((row) => [row.id, row.display_name]))),
      () => setStaff(new Map()),
    );
  }, []);
  const sections = new Map(
    state.kind === "ready" ? state.structure.sections.map((row) => [row.id, row.label]) : [],
  );
  return {
    section: (id: string) => sections.get(id) ?? id.slice(0, 8),
    person: (id: string | null | undefined) => (id ? (staff.get(id) ?? id.slice(0, 8)) : ""),
  };
}
