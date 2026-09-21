/**
 * Typed API surface for M14 platform.
 *
 * Shapes mirror contracts/M14/openapi.json.
 */

import { request, type Collection } from "@shared/api/client";

const BASE = "/api/v1";

export interface Job {
  readonly id: string;
  readonly kind: string;
  readonly school_id: string;
  readonly actor_id: string;
  readonly payload_ref: string;
  readonly state: "queued" | "running" | "succeeded" | "failed" | "dead";
  readonly progress: number;
  readonly error_code: string | null;
  readonly idempotency_key: string;
  readonly version: number;
  readonly created_at: string;
  readonly updated_at: string;
}

export interface AuditRecord {
  readonly id: string;
  readonly school_id: string;
  readonly actor_id: string;
  readonly action: string;
  readonly aggregate_id: string;
  readonly redacted_diff: { readonly before: Record<string, unknown>; readonly after: Record<string, unknown> };
  readonly request_id: string;
  readonly occurred_at: string;
}

export interface RestoreRehearsal {
  readonly id: string;
  readonly backup_manifest_id: string;
  readonly isolated_target_label: string;
  readonly state: string;
}

/** Scoped paginated audit log. */
export async function listAudit(options: {
  readonly action?: string;
  readonly actor_id?: string;
  readonly aggregate_id?: string;
  readonly occurred_from?: string;
  readonly occurred_to?: string;
  readonly cursor?: string;
} = {}): Promise<Collection<AuditRecord>> {
  return request<Collection<AuditRecord>>(`${BASE}/audit`, { query: options });
}

/** Job progress and sanitized error code. */
export async function getJob(jobId: string): Promise<Job> {
  return request<Job>(`${BASE}/jobs/${jobId}`);
}

/** Authorized replay preserving business idempotency. */
export async function retryJob(jobId: string, reason: string): Promise<Job> {
  return request<Job>(`${BASE}/jobs/${jobId}/retry`, {
    method: "POST",
    body: { reason },
  });
}

/** Operator-only isolated restore rehearsal. */
export async function createRestoreRehearsal(body: {
  readonly backup_manifest_id: string;
  readonly isolated_target_label: string;
}): Promise<RestoreRehearsal> {
  return request<RestoreRehearsal>(`${BASE}/operations/restore-rehearsals`, {
    method: "POST",
    body,
  });
}
