/** API helpers for M06 performance. */

import { request, type Collection } from "@shared/api/client";

const BASE = "/api/v1";

export type MetricDTO = {
  code: string;
  value: string | null;
  denominator: string | null;
  definition_version: number;
  status: string;
  window_label: string;
  cohort_label: string | null;
};

export type WarningSummary = {
  id: string;
  rule_id: string;
  state: string;
  explanation_key: string;
  student_id?: string | null;
};

export type DashboardDTO = {
  metrics: MetricDTO[];
  warnings: WarningSummary[];
  source_freshness: {
    assessment_updated_at: string | null;
    attendance_updated_at: string | null;
  };
  updated_at: string;
};

export type InterventionDTO = {
  id: string;
  school_id: string;
  student_id: string;
  goal: string;
  owner_id: string;
  review_date: string;
  state: string;
  visibility: string;
  version: number;
};

export async function fetchDashboard(
  studentId: string,
  window = "term",
): Promise<DashboardDTO> {
  return request<DashboardDTO>(`${BASE}/performance/dashboard`, {
    query: {
      scope: "student",
      window,
      student_id: studentId,
    },
  });
}

export async function dismissWarning(
  warningId: string,
  reason: string,
  expectedVersion: number,
): Promise<void> {
  await request(`${BASE}/warnings/${warningId}/dismiss`, {
    method: "POST",
    body: { reason, expected_version: expectedVersion },
  });
}

/** List interventions for one student. */
export async function listInterventions(
  studentId: string,
  cursor?: string,
): Promise<Collection<InterventionDTO>> {
  return request<Collection<InterventionDTO>>(`${BASE}/interventions`, {
    query: {
      student_id: studentId,
      cursor,
    },
  });
}
