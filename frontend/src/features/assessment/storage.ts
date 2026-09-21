/**
 * Browser session cache for assessment flows.
 *
 * M05 has no GET assessment/results endpoints yet; this keeps the last known
 * assessment wire and per-student attempt ids from successful PATCH responses
 * so marking can continue in the same browser session.
 */

import type { AssessmentDTO } from "./api";

const ASSESSMENT_KEY = "m05.assessment";
const ATTEMPT_PREFIX = "m05.attempt";

function assessmentStorageKey(assessmentId: string): string {
  return `${ASSESSMENT_KEY}:${assessmentId}`;
}

function attemptStorageKey(assessmentId: string, studentId: string): string {
  return `${ATTEMPT_PREFIX}:${assessmentId}:${studentId}`;
}

/** Remember one assessment DTO after create or workflow transitions. */
export function rememberAssessment(assessment: AssessmentDTO): void {
  sessionStorage.setItem(assessmentStorageKey(assessment.id), JSON.stringify(assessment));
}

/** Load a cached assessment DTO, if this session created or updated it. */
export function loadAssessment(assessmentId: string): AssessmentDTO | null {
  const raw = sessionStorage.getItem(assessmentStorageKey(assessmentId));
  if (raw === null) return null;
  try {
    return JSON.parse(raw) as AssessmentDTO;
  } catch {
    return null;
  }
}

/** Store the attempt id returned by a successful marks PATCH. */
export function rememberAttemptId(
  assessmentId: string,
  studentId: string,
  attemptId: string,
): void {
  sessionStorage.setItem(attemptStorageKey(assessmentId, studentId), attemptId);
}

/** Read a cached attempt id for one student on one assessment. */
export function loadAttemptId(assessmentId: string, studentId: string): string | null {
  return sessionStorage.getItem(attemptStorageKey(assessmentId, studentId));
}
