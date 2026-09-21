/**
 * Typed API surface for M10 alumni.
 *
 * Shapes mirror contracts/M10/openapi.json. No identity headers are sent.
 */

import { request, walkPages, type Collection } from "@shared/api/client";

const BASE = "/api/v1";

export type LeavingOutcome = "graduate" | "transfer";
export type CandidateState = "pending" | "approved" | "excluded";

export interface AlumniCandidate {
  readonly id: string;
  readonly school_id: string;
  readonly student_id: string;
  readonly leaving_event_id: string;
  readonly outcome: LeavingOutcome;
  readonly state: CandidateState;
  readonly version: number;
  readonly admission_no: string;
  readonly display_name: string;
  readonly last_standard: number;
  readonly leaving_year: number;
}

export interface ContactFields {
  readonly email?: string | null;
  readonly phone?: string | null;
  readonly postal_address?: string | null;
}

export interface ContactPreference {
  readonly person_id: string;
  readonly purpose: "alumni_notice" | "directory";
  readonly channel: "email" | "sms" | "postal" | "phone";
  readonly allowed: boolean;
  readonly updated_at: string;
}

export interface AlumniProfile {
  readonly id: string;
  readonly school_id: string;
  readonly student_id: string;
  readonly last_standard: number;
  readonly leaving_year: number;
  readonly outcome: LeavingOutcome;
  readonly snapshot_version: number;
  readonly contact_fields: ContactFields;
  readonly preferences: readonly ContactPreference[];
  readonly version: number;
  readonly display_name: string;
  readonly admission_no: string;
}

export interface ExportJob {
  readonly job_id: string;
  readonly state: "queued" | "running" | "succeeded" | "failed";
}

export type ExportField =
  | "display_name"
  | "admission_no"
  | "leaving_year"
  | "outcome"
  | "email"
  | "phone"
  | "postal_address";

/** List graduate/leaver candidates, optionally filtered by review state. */
export async function listCandidates(options: {
  readonly state?: CandidateState;
  readonly cursor?: string;
} = {}): Promise<Collection<AlumniCandidate>> {
  return request<Collection<AlumniCandidate>>(`${BASE}/alumni/candidates`, {
    query: { state: options.state, cursor: options.cursor },
  });
}

/** Paginated alumni directory with optional year and outcome filters. */
export async function listAlumni(options: {
  readonly year?: number;
  readonly outcome?: LeavingOutcome;
  readonly cursor?: string;
} = {}): Promise<Collection<AlumniProfile>> {
  return request<Collection<AlumniProfile>>(`${BASE}/alumni`, {
    query: { year: options.year, outcome: options.outcome, cursor: options.cursor },
  });
}

/** Walk every directory page until one profile matches id, or return null. */
export async function findAlumniById(alumniId: string): Promise<AlumniProfile | null> {
  for await (const page of walkPages<AlumniProfile>(`${BASE}/alumni`)) {
    const match = page.find((profile) => profile.id === alumniId);
    if (match !== undefined) return match;
  }
  return null;
}

/** Approve or exclude a pending candidate. */
export async function approveCandidate(
  candidateId: string,
  body: {
    readonly include: boolean;
    readonly reason: string;
    readonly contact_policy?: {
      readonly fields?: ContactFields;
      readonly preferences?: readonly {
        readonly purpose: ContactPreference["purpose"];
        readonly channel: ContactPreference["channel"];
        readonly allowed: boolean;
      }[];
    };
  },
): Promise<AlumniProfile | AlumniCandidate> {
  return request<AlumniProfile | AlumniCandidate>(
    `${BASE}/alumni/candidates/${candidateId}/approve`,
    { method: "POST", body },
  );
}

/** Update contact fields and preferences under optimistic concurrency. */
export async function patchAlumniContact(
  alumniId: string,
  body: {
    readonly expected_version: number;
    readonly reason: string;
    readonly fields?: ContactFields;
    readonly preferences?: readonly {
      readonly purpose: ContactPreference["purpose"];
      readonly channel: ContactPreference["channel"];
      readonly allowed: boolean;
    }[];
  },
): Promise<AlumniProfile> {
  return request<AlumniProfile>(`${BASE}/alumni/${alumniId}/contact`, {
    method: "PATCH",
    body,
  });
}

/** Enqueue an alumni export limited to granted fields. */
export async function createAlumniExport(body: {
  readonly filters: { readonly year?: number | null; readonly outcome?: LeavingOutcome | null };
  readonly fields: readonly ExportField[];
}): Promise<ExportJob> {
  return request<ExportJob>(`${BASE}/alumni/exports`, { method: "POST", body });
}
