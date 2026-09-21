/**
 * Load the school's structure once for pickers: the current academic year, its
 * sections labelled "Std 5 – A", and every subject.
 *
 * "Current" is the year marked active; failing that, the year whose dates
 * contain today; failing that, the latest. Does not handle: choosing a
 * different year (promotion screens pass their own).
 */

import { useEffect, useState } from "react";
import * as api from "./api";

export interface SectionOption {
  readonly id: string;
  readonly label: string;
  readonly standardNumber: number;
  readonly name: string;
}

export interface SchoolStructure {
  readonly year: api.AcademicYear | null;
  readonly sections: readonly SectionOption[];
  readonly subjects: readonly api.Subject[];
}

export type StructureState =
  | { readonly kind: "loading" }
  | { readonly kind: "ready"; readonly structure: SchoolStructure }
  | { readonly kind: "failed"; readonly error: unknown };

/** Pick the year the school is working in today. */
export function currentYear(
  years: readonly api.AcademicYear[],
  today: string,
): api.AcademicYear | null {
  const active = years.find((year) => year.state === "active");
  if (active) return active;
  const containing = years.find((year) => year.start <= today && today <= year.end);
  if (containing) return containing;
  return [...years].sort((a, b) => b.start.localeCompare(a.start))[0] ?? null;
}

/** Today's date in the school's timezone (India), as YYYY-MM-DD. */
export function schoolToday(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(new Date());
}

async function loadStructure(): Promise<SchoolStructure> {
  const [years, standards, sections, subjects] = await Promise.all([
    api.listAllAcademicYears(),
    api.listAllStandards(),
    api.listAllSections(),
    api.listAllSubjects(),
  ]);
  const year = currentYear(years, schoolToday());
  const numberById = new Map(standards.map((standard) => [standard.id, standard.number]));
  const options = sections
    .filter((section) => !section.archived && (year === null || section.year_id === year.id))
    .map((section) => {
      const standardNumber = numberById.get(section.standard_id) ?? 0;
      return {
        id: section.id,
        label: `Std ${standardNumber} – ${section.name}`,
        standardNumber,
        name: section.name,
      };
    })
    .sort((a, b) => a.standardNumber - b.standardNumber || a.name.localeCompare(b.name));
  return {
    year,
    sections: options,
    subjects: subjects
      .filter((subject) => !subject.archived)
      .sort((a, b) => a.display_name.localeCompare(b.display_name)),
  };
}

/** React hook wrapper around loadStructure, with a reload function. */
export function useSchoolStructure(): { state: StructureState; reload: () => void } {
  const [state, setState] = useState<StructureState>({ kind: "loading" });
  const [generation, setGeneration] = useState(0);

  useEffect(() => {
    let cancelled = false;
    loadStructure().then(
      (structure) => {
        if (!cancelled) setState({ kind: "ready", structure });
      },
      (error: unknown) => {
        if (!cancelled) setState({ kind: "failed", error });
      },
    );
    return () => {
      cancelled = true;
    };
  }, [generation]);

  return { state, reload: () => setGeneration((value) => value + 1) };
}
