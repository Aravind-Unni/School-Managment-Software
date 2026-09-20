/** API helpers for M06 performance. */

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

export async function fetchDashboard(
  studentId: string,
  window = "term",
): Promise<DashboardDTO> {
  const params = new URLSearchParams({
    scope: "student",
    window,
    student_id: studentId,
  });
  const res = await fetch(`/api/v1/performance/dashboard?${params.toString()}`, {
    credentials: "include",
  });
  if (!res.ok) {
    throw new Error(`dashboard_failed_${res.status}`);
  }
  return (await res.json()) as DashboardDTO;
}

export async function dismissWarning(
  warningId: string,
  reason: string,
  expectedVersion: number,
): Promise<void> {
  const res = await fetch(`/api/v1/warnings/${warningId}/dismiss`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason, expected_version: expectedVersion }),
  });
  if (!res.ok) {
    throw new Error(`dismiss_failed_${res.status}`);
  }
}
