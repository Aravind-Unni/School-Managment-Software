/**
 * Typed API surface for M08 transport.
 *
 * Shapes mirror contracts/M08/openapi.json.
 */

import { request, type Collection } from "@shared/api/client";

const BASE = "/api/v1";

export interface ParticipantRowDTO {
  readonly participation_id: string;
  readonly student_id: string;
  readonly display_name: string;
  readonly bus_id: string | null;
  readonly from_date: string;
  readonly to_date: string | null;
  readonly fee_plan_id: string;
}

export interface BillingRunDTO {
  readonly job_id: string;
  readonly state: "queued" | "running" | "succeeded" | "failed";
  readonly period: string;
  readonly policy_version: number;
  readonly preview: {
    readonly eligible_count: number;
    readonly blocked_count: number;
    readonly already_billed_count: number;
  };
}

export interface ReconciliationItemDTO {
  readonly kind: "missing_charge" | "orphaned_link" | "blocked" | "retryable_failure";
  readonly owner: "transport" | "fees";
  readonly period: string;
  readonly retryable: boolean;
  readonly participation_id: string | null;
  readonly billing_request_id: string | null;
  readonly source_key: string | null;
  readonly charge_id: string | null;
  readonly state: string | null;
  readonly error_code: string | null;
}

export interface ReconciliationDTO {
  readonly period: string;
  readonly items: readonly ReconciliationItemDTO[];
}

/** Paginated effective bus participants on a school date. */
export async function listBusParticipants(
  date: string,
  cursor?: string,
): Promise<Collection<ParticipantRowDTO>> {
  return request<Collection<ParticipantRowDTO>>(`${BASE}/bus-participants`, {
    query: { date, cursor },
  });
}

/** Unmatched participation/charge requests and retry status for one period. */
export async function getBillingReconciliation(period: string): Promise<ReconciliationDTO> {
  return request<ReconciliationDTO>(`${BASE}/bus-billing-reconciliation`, {
    query: { period },
  });
}

/** Queue a period billing run with validation preview. */
export async function createBillingRun(body: {
  readonly period: string;
  readonly policy_version: number;
}): Promise<BillingRunDTO> {
  return request<BillingRunDTO>(`${BASE}/bus-billing-runs`, { method: "POST", body });
}
