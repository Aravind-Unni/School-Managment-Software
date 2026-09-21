/**
 * Typed API surface for M02 registry.
 *
 * Request and response shapes mirror contracts/M02/openapi.json. Identity is never
 * sent from the client; the shared request() helper enforces that.
 */

import { fetchAll, request, type Collection } from "@shared/api/client";

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
  readonly settings?: SchoolSettings;
}

/** School-wide settings installed from the school's config file. */
export interface SchoolSettings {
  readonly timezone?: string;
  readonly currency?: string;
  readonly working_days?: readonly number[];
  readonly grading_bands?: readonly { readonly grade: string; readonly min_percent: number }[];
  readonly low_attendance_percent?: number;
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
  readonly code: string;
  readonly display_name: string;
  readonly archived: boolean;
}

export interface Standard {
  readonly id: string;
  readonly school_id: string;
  readonly version: number;
  readonly number: number;
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

// --- whole-collection reads for pickers ---------------------------------------

/** Every standard (class level). Small: at most twelve. */
export async function listAllStandards(): Promise<Standard[]> {
  return fetchAll<Standard>(`${BASE}/standards`, { pageSize: 100 });
}

/** Every section of every year. A school has tens to low hundreds. */
export async function listAllSections(): Promise<Section[]> {
  return fetchAll<Section>(`${BASE}/sections`, { pageSize: 100 });
}

/** Every subject. */
export async function listAllSubjects(): Promise<Subject[]> {
  return fetchAll<Subject>(`${BASE}/subjects`, { pageSize: 100 });
}

/** Every academic year. */
export async function listAllAcademicYears(): Promise<AcademicYear[]> {
  return fetchAll<AcademicYear>(`${BASE}/academic-years`, { pageSize: 100 });
}

/** Every staff member (for pickers). */
export async function listAllStaff(): Promise<StaffMember[]> {
  return fetchAll<StaffMember>(`${BASE}/staff`, { pageSize: 100 });
}

/** Every guardian (for pickers). */
export async function listAllGuardians(): Promise<Guardian[]> {
  return fetchAll<Guardian>(`${BASE}/guardians`, { pageSize: 100 });
}

// --- writes -------------------------------------------------------------------

/** Admit a student. Guardians may be linked in the same call. */
export async function createStudent(input: {
  readonly admissionNo: string;
  readonly displayName: string;
  readonly dateOfBirth: string | null;
  readonly preferredLanguage: "en" | "ml";
  readonly guardianLinks?: readonly { readonly guardianId: string; readonly fromDate: string }[];
}): Promise<StudentRecord> {
  return request<StudentRecord>(`${BASE}/students`, {
    method: "POST",
    body: {
      admission_no: input.admissionNo,
      display_name: input.displayName,
      profile: {
        date_of_birth: input.dateOfBirth,
        preferred_language: input.preferredLanguage,
      },
      guardian_links: (input.guardianLinks ?? []).map((link) => ({
        guardian_id: link.guardianId,
        visibility: "academic",
        from_date: link.fromDate,
        to_date: null,
      })),
      external_ids: [],
      duplicate_review: null,
    },
  });
}

/** Add a parent or guardian. */
export async function createGuardian(input: {
  readonly displayName: string;
  readonly email: string | null;
  readonly phone: string | null;
}): Promise<Guardian> {
  return request<Guardian>(`${BASE}/guardians`, {
    method: "POST",
    body: {
      display_name: input.displayName,
      email: input.email,
      phone: input.phone,
      external_ids: [],
    },
  });
}

/** Add a staff member. */
export async function createStaff(input: { readonly displayName: string }): Promise<StaffMember> {
  return request<StaffMember>(`${BASE}/staff`, {
    method: "POST",
    body: { display_name: input.displayName, external_ids: [] },
  });
}

/** Link a guardian to a student from a date. */
export async function createGuardianLink(input: {
  readonly studentId: string;
  readonly guardianId: string;
  readonly fromDate: string;
}): Promise<{ readonly id: string }> {
  return request<{ readonly id: string }>(`${BASE}/guardian-links`, {
    method: "POST",
    body: {
      student_id: input.studentId,
      guardian_id: input.guardianId,
      visibility: "academic",
      from_date: input.fromDate,
      to_date: null,
    },
  });
}

/** Put a student in a section for a year (also enrols them in its subjects). */
export async function createEnrolment(input: {
  readonly studentId: string;
  readonly yearId: string;
  readonly sectionId: string;
  readonly fromDate: string;
}): Promise<{ readonly id: string }> {
  return request<{ readonly id: string }>(`${BASE}/enrolments`, {
    method: "POST",
    body: {
      student_id: input.studentId,
      year_id: input.yearId,
      section_id: input.sectionId,
      from_date: input.fromDate,
      to_date: null,
    },
  });
}

/** Assign a teacher to teach a subject to a section. */
export async function createTeachingAssignment(input: {
  readonly staffId: string;
  readonly sectionId: string;
  readonly subjectId: string;
  readonly fromDate: string;
}): Promise<{ readonly id: string }> {
  return request<{ readonly id: string }>(`${BASE}/teaching-assignments`, {
    method: "POST",
    body: {
      staff_id: input.staffId,
      section_id: input.sectionId,
      subject_id: input.subjectId,
      from_date: input.fromDate,
      to_date: null,
    },
  });
}
