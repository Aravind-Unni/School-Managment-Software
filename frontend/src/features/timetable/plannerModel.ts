/**
 * Pure planner logic: the week grid, who teaches what, clashes and loads.
 * No IO; the planner page loads data and calls these.
 */

export interface PeriodRow {
  readonly day_of_week: number;
  readonly slot_code: string;
  readonly starts_at_local: string;
  readonly ends_at_local: string;
}

export interface Cell {
  readonly subjectId: string;
  readonly teacherId: string;
}

/** Grid of every section's week: key(section, day, code) -> cell. */
export type Grid = ReadonlyMap<string, Cell>;

export const cellKey = (sectionId: string, day: number, code: string) =>
  `${sectionId}|${day}|${code}`;

export const DAY_NAMES = ["", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
export const DAY_SHORT = ["", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

/** Build a grid from a timetable's slots. */
export function gridFromSlots(
  slots: readonly {
    section_id: string;
    day_of_week: number;
    slot_code: string;
    subject_id: string;
    teacher_id: string;
  }[],
): Map<string, Cell> {
  const grid = new Map<string, Cell>();
  for (const slot of slots) {
    grid.set(cellKey(slot.section_id, slot.day_of_week, slot.slot_code), {
      subjectId: slot.subject_id,
      teacherId: slot.teacher_id,
    });
  }
  return grid;
}

/** Turn the grid back into the API's slot list. */
export function slotsFromGrid(grid: Grid) {
  return [...grid.entries()].map(([key, cell]) => {
    const [sectionId, day, code] = key.split("|");
    return {
      day_of_week: Number(day),
      slot_code: code ?? "",
      section_id: sectionId ?? "",
      subject_id: cell.subjectId,
      teacher_id: cell.teacherId,
      room_code: null,
    };
  });
}

/** Days and period codes (ordered by start time) present in the bell schedule. */
export function weekShape(periods: readonly PeriodRow[]) {
  const days = [...new Set(periods.map((row) => row.day_of_week))].sort((a, b) => a - b);
  const firstDay = days[0];
  const codes = periods
    .filter((row) => row.day_of_week === firstDay)
    .sort((a, b) => a.starts_at_local.localeCompare(b.starts_at_local))
    .map((row) => ({ code: row.slot_code, start: row.starts_at_local, end: row.ends_at_local }));
  return { days, codes };
}

/**
 * Return the other section a teacher is already teaching in this period, if
 * any. A teacher can only be in one room at a time.
 */
export function clashFor(
  grid: Grid,
  sectionId: string,
  day: number,
  code: string,
  teacherId: string,
): string | null {
  for (const [key, cell] of grid) {
    if (cell.teacherId !== teacherId) continue;
    const [otherSection, otherDay, otherCode] = key.split("|");
    if (otherSection !== sectionId && Number(otherDay) === day && otherCode === code) {
      return otherSection ?? null;
    }
  }
  return null;
}

/** Periods per week each subject has in one section. */
export function subjectLoad(grid: Grid, sectionId: string): Map<string, number> {
  const load = new Map<string, number>();
  for (const [key, cell] of grid) {
    if (!key.startsWith(`${sectionId}|`)) continue;
    load.set(cell.subjectId, (load.get(cell.subjectId) ?? 0) + 1);
  }
  return load;
}

/** Periods per week each teacher teaches across the whole school. */
export function teacherLoad(grid: Grid): Map<string, number> {
  const load = new Map<string, number>();
  for (const cell of grid.values()) {
    load.set(cell.teacherId, (load.get(cell.teacherId) ?? 0) + 1);
  }
  return load;
}

/** Re-point every period of (section, subject) to a new teacher. */
export function reassignTeacher(
  grid: Grid,
  sectionId: string,
  subjectId: string,
  teacherId: string,
): Map<string, Cell> {
  const next = new Map(grid);
  for (const [key, cell] of grid) {
    if (key.startsWith(`${sectionId}|`) && cell.subjectId === subjectId) {
      next.set(key, { subjectId, teacherId });
    }
  }
  return next;
}
