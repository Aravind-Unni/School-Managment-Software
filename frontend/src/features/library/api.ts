/**
 * Typed API surface for M09 library.
 *
 * Shapes mirror contracts/M09/openapi.json.
 */

import { request, type Collection } from "@shared/api/client";

const BASE = "/api/v1";

export interface TitleDTO {
  readonly id: string;
  readonly school_id: string;
  readonly isbn: string | null;
  readonly name: string;
  readonly author: string;
  readonly language: string;
  readonly version: number;
}

export interface AvailabilityView {
  readonly available: number;
  readonly total: number;
}

export interface LoanDTO {
  readonly id: string;
  readonly school_id: string;
  readonly copy_id: string;
  readonly borrower_person_id: string;
  readonly borrower_type: "student" | "staff";
  readonly issued_at: string;
  readonly due_date: string;
  readonly returned_at: string | null;
  readonly version: number;
}

export interface OverdueItemDTO {
  readonly loan_id: string;
  readonly copy_id: string;
  readonly accession_no: string;
  readonly borrower_person_id: string;
  readonly borrower_display_name: string;
  readonly due_date: string;
  readonly as_of: string;
}

/** Search catalogue titles. */
export async function searchTitles(
  query: { readonly q?: string; readonly cursor?: string } = {},
): Promise<Collection<TitleDTO>> {
  return request<Collection<TitleDTO>>(`${BASE}/library/titles`, { query });
}

/** Available and total copy counts for one title. */
export async function getTitleAvailability(titleId: string): Promise<AvailabilityView> {
  return request<AvailabilityView>(`${BASE}/library/titles/${titleId}/availability`);
}

/** Issue a copy to a borrower. */
export async function issueLoan(
  body: {
    readonly copy_id: string;
    readonly borrower_person_id: string;
    readonly borrower_type: "student" | "staff";
    readonly due_date: string;
  },
  idempotencyKey: string,
): Promise<LoanDTO> {
  return request<LoanDTO>(`${BASE}/library/loans`, {
    method: "POST",
    body,
    headers: { "Idempotency-Key": idempotencyKey },
  });
}

/** Return an open loan. */
export async function returnLoan(
  loanId: string,
  body: {
    readonly returned_at: string;
    readonly condition: "ok" | "damaged" | "lost";
    readonly expected_version: number;
  },
): Promise<LoanDTO> {
  return request<LoanDTO>(`${BASE}/library/loans/${loanId}/return`, {
    method: "POST",
    body,
  });
}

/** Overdue open loans as of a school civil date. */
export async function listOverdues(
  asOf: string,
  cursor?: string,
): Promise<Collection<OverdueItemDTO>> {
  return request<Collection<OverdueItemDTO>>(`${BASE}/library/overdues`, {
    query: { as_of: asOf, cursor },
  });
}
