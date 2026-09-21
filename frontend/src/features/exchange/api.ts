/**
 * Typed API surface for M13 exchange.
 *
 * Shapes mirror contracts/M13/openapi.json.
 */

import { request, type Collection } from "@shared/api/client";

const BASE = "/api/v1";

export type ImportDataset = "enrolments" | "opening_balances" | "results" | "library_loans";
export type ExportDataset =
  | "attendance_summary"
  | "progress"
  | "at_risk"
  | "ptm_summary"
  | "class_roster"
  | "subject_summary";
export type ExchangeLocale = "en" | "ml";

export interface ImportTemplate {
  readonly dataset: ImportDataset;
  readonly schema_version: string;
  readonly columns: readonly string[];
  readonly sample_csv_url?: string;
}

export interface ImportJob {
  readonly id: string;
  readonly school_id: string;
  readonly dataset: ImportDataset;
  readonly state: string;
  readonly file_ref: string;
  readonly validation_version: number;
  readonly source_digest: string | null;
  readonly accepted_count: number;
  readonly error_count: number;
  readonly applied_count: number;
}

export interface ImportRowError {
  readonly row: number;
  readonly field: string;
  readonly code: string;
}

export interface ExportJob {
  readonly id: string;
  readonly school_id: string;
  readonly dataset: ExportDataset;
  readonly format: "csv" | "xlsx" | "pdf";
  readonly locale: ExchangeLocale;
  readonly state: string;
  readonly artifact_ref: string | null;
}

export interface ReportCardJob {
  readonly id: string;
  readonly school_id: string;
  readonly publication_id: string;
  readonly student_id: string;
  readonly locale: ExchangeLocale;
  readonly template_version: string;
  readonly state: string;
}

export interface ReportSnapshot {
  readonly id: string;
  readonly type: string;
  readonly source_revision_ids: readonly string[];
  readonly policy_versions: Record<string, unknown>;
  readonly locale: ExchangeLocale;
  readonly artifact_ref: unknown;
  readonly state: string;
}

export interface ArtifactAccess {
  readonly authorized_read_url: string;
  readonly expires_at: string;
}

/** Column schema for a bulk import dataset. */
export async function getImportTemplate(dataset: ImportDataset): Promise<ImportTemplate> {
  return request<ImportTemplate>(`${BASE}/import-templates/${dataset}`);
}

/** Start validate-only import for an uploaded file reference. */
export async function createImport(body: {
  readonly dataset: ImportDataset;
  readonly file_ref: string;
  readonly mode: "validate";
}): Promise<{ readonly job_id: string; readonly template_version: string; readonly schema_version: string }> {
  return request(`${BASE}/imports`, { method: "POST", body });
}

/** Import job status and row counts. */
export async function getImport(importId: string): Promise<ImportJob> {
  return request<ImportJob>(`${BASE}/imports/${importId}`);
}

/** Paginated validation errors for a job. */
export async function listImportErrors(
  importId: string,
  cursor?: string,
): Promise<Collection<ImportRowError>> {
  return request<Collection<ImportRowError>>(`${BASE}/imports/${importId}/errors`, {
    query: { cursor },
  });
}

/** Apply validated rows after digest check. */
export async function commitImport(
  importId: string,
  body: { readonly validation_version: number; readonly source_digest: string },
  idempotencyKey: string,
): Promise<ImportJob> {
  return request<ImportJob>(`${BASE}/imports/${importId}/commit`, {
    method: "POST",
    body,
    headers: { "Idempotency-Key": idempotencyKey },
  });
}

/** Enqueue a dataset export. */
export async function createExport(body: {
  readonly dataset: ExportDataset;
  readonly filters: Record<string, unknown>;
  readonly fields: readonly string[];
  readonly format: "csv" | "xlsx" | "pdf";
  readonly locale: ExchangeLocale;
}): Promise<ExportJob> {
  return request<ExportJob>(`${BASE}/exports`, { method: "POST", body });
}

/** Export job status. */
export async function getExport(exportId: string): Promise<ExportJob> {
  return request<ExportJob>(`${BASE}/exports/${exportId}`);
}

/** Short-lived read URL for a ready export artifact. */
export async function downloadExport(exportId: string): Promise<ArtifactAccess> {
  return request<ArtifactAccess>(`${BASE}/exports/${exportId}/download`);
}

/** Enqueue report card generation for students. */
export async function createReportCards(body: {
  readonly publication_id: string;
  readonly student_ids: readonly string[];
  readonly locale: ExchangeLocale;
  readonly template_version: string;
}): Promise<{ readonly jobs: readonly ReportCardJob[] }> {
  return request(`${BASE}/reportcards`, { method: "POST", body });
}

/** Report card job status. */
export async function getReportCardJob(jobId: string): Promise<ReportCardJob> {
  return request<ReportCardJob>(`${BASE}/reportcards/${jobId}`);
}

/** Immutable report snapshot metadata. */
export async function getReportSnapshot(reportId: string): Promise<ReportSnapshot> {
  return request<ReportSnapshot>(`${BASE}/reports/${reportId}`);
}

/** Short-lived read URL for a report artifact. */
export async function downloadReport(reportId: string): Promise<ArtifactAccess> {
  return request<ArtifactAccess>(`${BASE}/reports/${reportId}/download`);
}
