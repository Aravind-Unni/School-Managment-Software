/**
 * Typed API surface for M03 timetable.
 *
 * Every request and response shape comes from the GENERATED schema, which is
 * produced from the frozen `contracts/M03/openapi.json`. Hand-writing them would
 * let the client drift from the contract silently, which is exactly the failure
 * the contract exists to prevent.
 *
 * No function here sends an identity header, a school id or a relationship
 * claim: the server derives all three, and the shared client refuses to send
 * them even if asked.
 */

import { request, type Collection } from "@shared/api/client";
import type { components } from "./generated/schema";

type Schemas = components["schemas"];

export type TimetableVersion = Schemas["TimetableVersionDTO"];
export type TimetableSummary = Schemas["TimetableSummaryDTO"];
export type PeriodTemplate = Schemas["PeriodTemplateDTO"];
export type Slot = Schemas["SlotDTO"];
export type Conflict = Schemas["ConflictDTO"];
export type ValidationReport = Schemas["ValidationReportDTO"];
export type PublishResult = Schemas["PublishResultDTO"];
export type PeriodSession = Schemas["PeriodSessionDTO"];
export type SectionDay = Schemas["SectionDayDTO"];
export type TeacherDay = Schemas["TeacherDayDTO"];
export type StudentDay = Schemas["StudentDayDTO"];
export type CalendarRange = Schemas["CalendarDTO"];
export type CalendarDay = Schemas["CalendarDayDTO"];
export type CalendarException = Schemas["CalendarExceptionDTO"];
export type Substitution = Schemas["SubstitutionDTO"];
export type PeriodTemplateInput = Schemas["PeriodTemplateRequest"];
export type SlotInput = Schemas["SlotRequest"];

const BASE = "/api/v1";

/** List timetable revisions, newest effective range first. */
export async function listTimetables(
  options: { readonly state?: string; readonly cursor?: string } = {},
): Promise<Collection<TimetableSummary>> {
  const query: Record<string, string | undefined> = {};
  if (options.state !== undefined) query["state"] = options.state;
  if (options.cursor !== undefined) query["cursor"] = options.cursor;
  return request<Collection<TimetableSummary>>(`${BASE}/timetables`, { query });
}

/** Read one revision with its whole grid. */
export async function readTimetable(timetableId: string): Promise<TimetableVersion> {
  return request<TimetableVersion>(`${BASE}/timetables/${timetableId}`);
}

/** Create a draft revision. It is never published by this call. */
export async function createTimetable(input: {
  readonly yearId: string;
  readonly effectiveFrom: string;
  readonly effectiveTo?: string | null;
  readonly periods: readonly PeriodTemplateInput[];
  readonly slots: readonly SlotInput[];
}): Promise<TimetableVersion> {
  return request<TimetableVersion>(`${BASE}/timetables`, {
    method: "POST",
    body: {
      year_id: input.yearId,
      effective_from: input.effectiveFrom,
      effective_to: input.effectiveTo ?? null,
      periods: input.periods,
      slots: input.slots,
    },
  });
}

/**
 * Replace a draft's whole grid.
 *
 * `expectedVersion` is mandatory. Omitting it would be a last-write-wins
 * overwrite of another editor's week; the server answers 409 on a mismatch.
 */
export async function replaceTimetable(
  timetableId: string,
  input: {
    readonly effectiveFrom: string;
    readonly effectiveTo?: string | null;
    readonly periods: readonly PeriodTemplateInput[];
    readonly slots: readonly SlotInput[];
    readonly expectedVersion: number;
  },
): Promise<TimetableVersion> {
  return request<TimetableVersion>(`${BASE}/timetables/${timetableId}`, {
    method: "PUT",
    body: {
      effective_from: input.effectiveFrom,
      effective_to: input.effectiveTo ?? null,
      periods: input.periods,
      slots: input.slots,
      expected_version: input.expectedVersion,
    },
  });
}

/** Ask which conflicts stand in a draft. Read-only; it reserves nothing. */
export async function validateTimetable(timetableId: string): Promise<ValidationReport> {
  return request<ValidationReport>(`${BASE}/timetables/${timetableId}/validate`, {
    method: "POST",
  });
}

/** Publish a draft under the version the editor last read. */
export async function publishTimetable(
  timetableId: string,
  expectedVersion: number,
): Promise<PublishResult> {
  return request<PublishResult>(`${BASE}/timetables/${timetableId}/publish`, {
    method: "POST",
    body: { expected_version: expectedVersion },
  });
}

/** Read one section's effective schedule for a date. */
export async function readSectionDay(input: {
  readonly sectionId: string;
  readonly date: string;
  readonly studentId?: string;
}): Promise<SectionDay> {
  const query: Record<string, string | undefined> = {
    section_id: input.sectionId,
    date: input.date,
  };
  if (input.studentId !== undefined) query["student_id"] = input.studentId;
  return request<SectionDay>(`${BASE}/timetables/current`, { query });
}

/** Read one teacher's dated schedule, including the periods they are covering. */
export async function readTeacherDay(staffId: string, date: string): Promise<TeacherDay> {
  return request<TeacherDay>(`${BASE}/teacher-schedule`, {
    query: { staff_id: staffId, date },
  });
}

/** Read one pupil's dated schedule, marked with the subjects they take. */
export async function readStudentDay(studentId: string, date: string): Promise<StudentDay> {
  return request<StudentDay>(`${BASE}/student-schedule`, {
    query: { student_id: studentId, date },
  });
}

/** Read the school calendar over an inclusive, bounded range. */
export async function readCalendar(fromDate: string, toDate: string): Promise<CalendarRange> {
  return request<CalendarRange>(`${BASE}/calendar`, {
    query: { from_date: fromDate, to_date: toDate },
  });
}

/** Record a calendar exception, reinstating a withdrawn one for the same date. */
export async function recordCalendarException(input: {
  readonly date: string;
  readonly kind: "holiday" | "exam" | "event";
  readonly reasonKey?: string | null;
}): Promise<CalendarException> {
  return request<CalendarException>(`${BASE}/calendar-exceptions`, {
    method: "POST",
    body: { date: input.date, kind: input.kind, reason_key: input.reasonKey ?? null },
  });
}

/** List substitutions for a date. */
export async function listSubstitutions(
  date: string,
): Promise<Collection<Substitution>> {
  return request<Collection<Substitution>>(`${BASE}/substitutions`, { query: { date } });
}

/**
 * Assign a substitute to one dated period.
 *
 * `validUntil` is left to the server unless the caller narrows it: the default
 * is the end of that school day, and the server refuses anything later.
 */
export async function assignSubstitution(input: {
  readonly date: string;
  readonly slotId: string;
  readonly teacherId: string;
  readonly reason: string;
  readonly validUntil?: string | null;
}): Promise<Substitution> {
  return request<Substitution>(`${BASE}/substitutions`, {
    method: "POST",
    body: {
      date: input.date,
      slot_id: input.slotId,
      teacher_id: input.teacherId,
      reason: input.reason,
      valid_until: input.validUntil ?? null,
    },
  });
}

/** Withdraw a substitution. Withdrawn, never deleted: a register may cite it. */
export async function withdrawSubstitution(
  substitutionId: string,
  expectedVersion: number,
): Promise<Substitution> {
  return request<Substitution>(`${BASE}/substitutions/${substitutionId}`, {
    method: "PUT",
    body: { withdrawn: true, expected_version: expectedVersion },
  });
}

/**
 * Cancel or restore one dated period.
 *
 * `expectedVersion` is null on the first cancellation of a session, which has no
 * override record yet. Afterwards it is the number of changes this client has
 * made: the frozen PeriodSessionDTO carries no version to read back.
 */
export async function setSessionCancellation(
  timetableSessionId: string,
  input: {
    readonly cancelled: boolean;
    readonly reasonKey?: string | null;
    readonly expectedVersion: number | null;
  },
): Promise<PeriodSession> {
  return request<PeriodSession>(`${BASE}/sessions/${timetableSessionId}/cancellation`, {
    method: "PUT",
    body: {
      cancelled: input.cancelled,
      reason_key: input.reasonKey ?? null,
      expected_version: input.expectedVersion,
    },
  });
}
