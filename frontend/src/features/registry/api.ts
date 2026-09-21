/**
 * Typed API surface for M02 registry.
 *
 * Request and response shapes mirror contracts/M02/openapi.json. Identity is never
 * sent from the client; the shared request() helper enforces that.
 */

import { request, type Collection } from "@shared/api/client";

const BASE = "/api/v1";

export type StudentStatus = "active" | "inactive" | "transferred" | "graduated";

export interface Profile {
  readonly date_of_birth: string | null;
  readonly preferred_language: "en" | "ml";
}

export interface ExternalId {
  readonly source: string;
  readonly value: string;
}

export interface StudentRecord {
  readonly id: string;
  readonly school_id: string;
  readonly version: number;
  readonly admission_no: string;
  readonly display_name: string;
  readonly status: StudentStatus;
  readonly profile: Profile;
  readonly external_ids: readonly ExternalId[];
  readonly archived: boolean;
}

export interface Guardian {
  readonly id: string;
  readonly school_id: string;
  readonly version: number;
  readonly display_name: string;
  readonly email: string | null;
  readonly phone: string | null;
  readonly external_ids: readonly ExternalId[];
  readonly archived: boolean;
}

export interface StaffMember {
  readonly id: string;
  readonly school_id: string;
  readonly version: number;
  readonly display_name: string;
  readonly external_ids: readonly ExternalId[];
  readonly archived: boolean;
}

export interface Section {
  readonly id: string;
  readonly school_id: string;
  readonly version: number;
  readonly year_id: string;
  readonly standard_id: string;
  readonly name: string;
  readonly archived: boolean;
}

export interface SchoolConfig {
  readonly id: string;
  readonly school_id: string;
  readonly version: number;
  readonly display_name: string;
  readonly board: "CBSE";
  readonly default_language: "en" | "ml";
}

export interface AcademicYear {
  readonly id: string;
  readonly school_id: string;
  readonly version: number;
  readonly name: string;
  readonly start: string;
  readonly end: string;
  readonly state: string;
}

export interface Term {
  readonly id: string;
  readonly school_id: string;
  readonly version: number;
  readonly year_id: string;
  readonly name: string;
  readonly start: string;
  readonly end: string;
  readonly state: string;
}

export interface Subject {
  readonly id: string;
  readonly school_id: string;
  readonly version: number;
  readonly name: string;
  readonly archived: boolean;
}

export interface RosterStudent {
  readonly student_id: string;
  readonly enrolment_id: string;
  readonly display_name: string;
}

export interface RosterDTO {
  readonly section_id: string;
  readonly date: string;
  readonly subject_id: string | null;
  readonly version: number;
  readonly students: readonly RosterStudent[];
}

/** List students with optional text search and cursor pagination. */
export async function listStudents(options: {
  readonly cursor?: string;
  readonly pageSize?: number;
  readonly query?: string;
} = {}): Promise<Collection<StudentRecord>> {
  return request<Collection<StudentRecord>>(`${BASE}/students`, {
    query: {
      cursor: options.cursor,
      page_size: options.pageSize,
      query: options.query,
    },
  });
}

/** Fetch one student record by id. */
export async function getStudent(studentId: string): Promise<StudentRecord> {
  return request<StudentRecord>(`${BASE}/students/${studentId}`);
}

/** List guardians with cursor pagination. */
export async function listGuardians(options: {
  readonly cursor?: string;
  readonly pageSize?: number;
} = {}): Promise<Collection<Guardian>> {
  return request<Collection<Guardian>>(`${BASE}/guardians`, {
    query: {
      cursor: options.cursor,
      page_size: options.pageSize,
    },
  });
}

/** Fetch one guardian by id. */
export async function getGuardian(guardianId: string): Promise<Guardian> {
  return request<Guardian>(`${BASE}/guardians/${guardianId}`);
}

/** List staff with cursor pagination. */
export async function listStaff(options: {
  readonly cursor?: string;
  readonly pageSize?: number;
} = {}): Promise<Collection<StaffMember>> {
  return request<Collection<StaffMember>>(`${BASE}/staff`, {
    query: {
      cursor: options.cursor,
      page_size: options.pageSize,
    },
  });
}

/** Fetch one staff member by id. */
export async function getStaff(staffId: string): Promise<StaffMember> {
  return request<StaffMember>(`${BASE}/staff/${staffId}`);
}

/** List sections with cursor pagination. */
export async function listSections(options: {
  readonly cursor?: string;
  readonly pageSize?: number;
} = {}): Promise<Collection<Section>> {
  return request<Collection<Section>>(`${BASE}/sections`, {
    query: {
      cursor: options.cursor,
      page_size: options.pageSize,
    },
  });
}

/** Fetch one section by id. */
export async function getSection(sectionId: string): Promise<Section> {
  return request<Section>(`${BASE}/sections/${sectionId}`);
}

/** Read the installed school configuration. */
export async function getSchoolConfig(): Promise<SchoolConfig> {
  return request<SchoolConfig>(`${BASE}/school-config`);
}

/** List academic years with cursor pagination. */
export async function listAcademicYears(options: {
  readonly cursor?: string;
  readonly pageSize?: number;
} = {}): Promise<Collection<AcademicYear>> {
  return request<Collection<AcademicYear>>(`${BASE}/academic-years`, {
    query: {
      cursor: options.cursor,
      page_size: options.pageSize,
    },
  });
}

/** List terms with cursor pagination. */
export async function listTerms(options: {
  readonly cursor?: string;
  readonly pageSize?: number;
} = {}): Promise<Collection<Term>> {
  return request<Collection<Term>>(`${BASE}/terms`, {
    query: {
      cursor: options.cursor,
      page_size: options.pageSize,
    },
  });
}

/** List subjects with cursor pagination. */
export async function listSubjects(options: {
  readonly cursor?: string;
  readonly pageSize?: number;
} = {}): Promise<Collection<Subject>> {
  return request<Collection<Subject>>(`${BASE}/subjects`, {
    query: {
      cursor: options.cursor,
      page_size: options.pageSize,
    },
  });
}

/** Roster for one section on one date, optionally filtered to a subject offering. */
export async function getSectionRoster(
  sectionId: string,
  date: string,
  subjectId?: string,
): Promise<RosterDTO> {
  return request<RosterDTO>(`${BASE}/sections/${sectionId}/roster`, {
    query: {
      date,
      subject_id: subjectId,
    },
  });
}
