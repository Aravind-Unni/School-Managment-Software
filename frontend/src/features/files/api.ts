/**
 * Typed API surface for M12 files.
 *
 * Shapes mirror contracts/M12/openapi.json.
 */

import { request } from "@shared/api/client";

const BASE = "/api/v1";

export type FilePurpose = "answer_sheet_evidence";

export interface FileRecord {
  readonly id: string;
  readonly school_id: string;
  readonly state: string;
  readonly canonical_version: number | null;
  readonly sha256: string | null;
  readonly bytes: number | null;
  readonly width: number | null;
  readonly height: number | null;
  readonly profile_version: string | null;
  readonly review_confirmed: boolean;
  readonly rejection_reason: string | null;
}

export interface UploadSession {
  readonly id: string;
  readonly upload_url: string;
  readonly expires_at: string;
  readonly max_bytes: number;
}

/** Open a scoped upload session. */
export async function beginUpload(body: {
  readonly purpose: FilePurpose;
  readonly client_name: string;
  readonly declared_bytes: number;
  readonly mime: string;
}): Promise<UploadSession> {
  return request<UploadSession>(`${BASE}/uploads`, { method: "POST", body });
}

/** Verify quarantine bytes and enqueue processing. */
export async function completeUpload(
  sessionId: string,
  sourceSha256: string,
): Promise<{ readonly file_id: string; readonly state: "processing" }> {
  return request(`${BASE}/uploads/${sessionId}/complete`, {
    method: "POST",
    body: { source_sha256: sourceSha256 },
  });
}

/** File state and candidate metadata for review. */
export async function getFileStatus(fileId: string): Promise<FileRecord> {
  return request<FileRecord>(`${BASE}/files/${fileId}/status`);
}

/** Teacher confirms candidate readability. */
export async function confirmFileQuality(
  fileId: string,
  candidateVersion: number,
): Promise<FileRecord> {
  return request<FileRecord>(`${BASE}/files/${fileId}/quality-confirmation`, {
    method: "POST",
    body: { candidate_version: candidateVersion, readability_confirmed: true },
  });
}

/** Request higher-fidelity reprocess. */
export async function reprocessFile(fileId: string, reason: string): Promise<FileRecord> {
  return request<FileRecord>(`${BASE}/files/${fileId}/reprocess`, {
    method: "POST",
    body: { profile: "higher_fidelity", reason },
  });
}
