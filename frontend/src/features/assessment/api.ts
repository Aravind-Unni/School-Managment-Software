/**
 * Typed API surface for M05 assessment.
 *
 * Shapes mirror contracts/M05/openapi.json. No identity headers are sent.
 */

import { request } from "@shared/api/client";

const BASE = "/api/v1";

export interface ComponentDTO {
  readonly id: string;
  readonly max_score: string;
  readonly weight: string;
  readonly topic: string | null;
  readonly question_type: string | null;
}

export interface AssessmentDTO {
  readonly id: string;
  readonly school_id: string;
  readonly version: number;
  readonly year_id: string;
  readonly term_id: string;
  readonly section_id: string;
  readonly subject_id: string;
  readonly type: string;
  readonly max_score: string;
  readonly policy_version: string;
  readonly state: string;
  readonly components: readonly ComponentDTO[];
  readonly due_at: string | null;
}

export interface EvidenceRef {
  readonly binding_id: string;
  readonly file_id: string;
  readonly version: number;
  readonly sha256: string;
  readonly page_no: number;
}

export interface ResultDTO {
  readonly result_id: string;
  readonly revision_id: string;
  readonly assessment_id: string;
  readonly student_id: string;
  readonly subject_id: string;
  readonly attempt_id: string;
  readonly version: number;
  readonly status: string;
  readonly marking_outcome: string;
  readonly score: string | null;
  readonly max_score: string;
  readonly grade: string | null;
  readonly policy_version: string;
  readonly evidence_refs: readonly EvidenceRef[];
}

export interface PublicationResponse {
  readonly publication_id: string;
  readonly result_revision_ids: readonly string[];
  readonly report_job_id: string;
}

/** Create a draft assessment structure. */
export async function createAssessment(body: Record<string, unknown>): Promise<AssessmentDTO> {
  return request<AssessmentDTO>(`${BASE}/assessments`, { method: "POST", body });
}

/** Patch marks for one student. */
export async function patchResult(
  assessmentId: string,
  studentId: string,
  body: Record<string, unknown>,
): Promise<{ readonly result: ResultDTO; readonly version: number; readonly total: string | null }> {
  return request(`${BASE}/assessments/${assessmentId}/results/${studentId}`, {
    method: "PATCH",
    body,
  });
}

/** Submit for review. */
export async function submitAssessment(
  assessmentId: string,
  expectedVersion: number,
): Promise<AssessmentDTO> {
  return request<AssessmentDTO>(`${BASE}/assessments/${assessmentId}/submit`, {
    method: "POST",
    body: { expected_version: expectedVersion },
  });
}

/** Approve submitted results. */
export async function approveAssessment(
  assessmentId: string,
  expectedVersion: number,
): Promise<AssessmentDTO> {
  return request<AssessmentDTO>(`${BASE}/assessments/${assessmentId}/approve`, {
    method: "POST",
    body: { expected_version: expectedVersion },
  });
}

/** Publish approved results. Requires Idempotency-Key. */
export async function publishAssessment(
  assessmentId: string,
  expectedVersion: number,
  idempotencyKey: string,
): Promise<PublicationResponse> {
  return request<PublicationResponse>(`${BASE}/assessments/${assessmentId}/publication`, {
    method: "POST",
    body: { expected_version: expectedVersion },
    headers: { "Idempotency-Key": idempotencyKey },
  });
}

/** View one evidence binding. */
export async function viewEvidence(
  resultId: string,
  bindingId: string,
): Promise<{
  readonly read_url: string;
  readonly expires_at: string;
  readonly file_id: string;
  readonly version: number;
  readonly revision_id: string;
}> {
  return request(`${BASE}/results/${resultId}/evidence/${bindingId}/view`);
}
