/**
 * Typed API surface for M04 attendance.
 *
 * Shapes mirror contracts/M04/openapi.json. No identity headers are sent.
 */

import { request, type Collection } from "@shared/api/client";

const BASE = "/api/v1";

export type WritableStatus = "present" | "absent" | "late" | "excused";

export interface AuthorizedPeriod {
  readonly timetable_session_id: string;
  readonly date: string;
  readonly section_id: string;
  readonly slot_id: string;
  readonly slot_code: string;
  readonly subject_id: string;
  readonly assigned_teacher_id: string;
  readonly substitute_teacher_id: string | null;
  readonly starts_at: string;
  readonly ends_at: string;
  readonly cancelled: boolean;
  readonly timetable_version: number;
  readonly session_id: string | null;
  readonly submission_state: "unopened" | "draft" | "submitted";
  readonly missing_count: number;
  readonly section_label?: string | null;
  readonly subject_name?: string | null;
  readonly starts_at_local?: string;
  readonly ends_at_local?: string;
}

export interface RosterSnapshotEntry {
  readonly student_id: string;
  readonly enrolment_id: string;
  readonly display_name: string;
}

export interface AttendanceEntry {
  readonly id: string;
  readonly session_id: string;
  readonly enrolment_id: string;
  readonly student_id: string;
  readonly status: string;
  readonly note: string | null;
  readonly version: number;
}

export interface AttendanceSession {
  readonly id: string;
  readonly school_id: string;
  readonly timetable_session_id: string;
  readonly date: string;
  readonly section_id: string;
  readonly slot_id: string;
  readonly subject_id: string;
  readonly timetable_version: number;
  readonly roster_version: number;
  readonly roster_snapshot: readonly RosterSnapshotEntry[];
  readonly state: "draft" | "submitted";
  readonly version: number;
  readonly entries: readonly AttendanceEntry[];
  readonly submitted_at: string | null;
}

/** List the current actor's authorised periods for a school date. */
export async function listPeriods(date: string): Promise<Collection<AuthorizedPeriod>> {
  return request<Collection<AuthorizedPeriod>>(`${BASE}/attendance/periods`, {
    query: { date },
  });
}

/** Create a draft session or return the existing one. */
export async function createSession(timetableSessionId: string): Promise<AttendanceSession> {
  return request<AttendanceSession>(`${BASE}/attendance/sessions`, {
    method: "POST",
    body: { timetable_session_id: timetableSessionId },
  });
}

/** Save writable marks on a draft. */
export async function saveSession(
  sessionId: string,
  expectedVersion: number,
  entries: readonly { readonly enrolment_id: string; readonly status: WritableStatus }[],
): Promise<AttendanceSession> {
  return request<AttendanceSession>(`${BASE}/attendance/sessions/${sessionId}`, {
    method: "PUT",
    body: { expected_version: expectedVersion, entries },
  });
}

/** Submit a draft. Requires Idempotency-Key; failure must not look complete. */
export async function submitSession(
  sessionId: string,
  expectedVersion: number,
  idempotencyKey: string,
): Promise<AttendanceSession> {
  return request<AttendanceSession>(`${BASE}/attendance/sessions/${sessionId}/submit`, {
    method: "POST",
    body: { expected_version: expectedVersion },
    headers: { "Idempotency-Key": idempotencyKey },
  });
}
