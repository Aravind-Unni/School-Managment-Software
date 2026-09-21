/**
 * Typed API surface for M07 fees.
 *
 * Shapes mirror contracts/M07/openapi.json. No identity headers are sent.
 */

import { request, type Collection } from "@shared/api/client";

const BASE = "/api/v1";

export type BalanceDTO = {
  readonly student_id: string | null;
  readonly charged_paise: number;
  readonly credited_paise: number;
  readonly paid_paise: number;
  readonly outstanding_paise: number;
  readonly overdue_paise: number;
  readonly credit_available_paise: number;
  readonly as_of: string;
};

export type FeeStatementDTO = {
  readonly student_id: string;
  readonly as_of: string;
  readonly entries: ReadonlyArray<{
    readonly entry_type: string;
    readonly id: string;
    readonly amount_paise: number;
    readonly posted_at: string;
    readonly description_key: string;
  }>;
  readonly balance: BalanceDTO;
  readonly student_display_name: string | null;
};

export type PaymentReceiptDTO = {
  readonly payment: {
    readonly id: string;
    readonly number: string;
    readonly amount_paise: number;
    readonly method: string;
    readonly version: number;
  };
  readonly balance: BalanceDTO;
};

export type PaymentDTO = {
  readonly id: string;
  readonly number: string;
  readonly amount_paise: number;
  readonly method: string;
  readonly version: number;
};

export type FeeHeadDTO = {
  readonly id: string;
  readonly school_id: string;
  readonly code: string;
  readonly label_key: string;
  readonly version: number;
};

export type FeePlanDTO = {
  readonly id: string;
  readonly school_id: string;
  readonly version: number;
  readonly applicability: {
    readonly standards?: readonly number[];
    readonly section_ids?: readonly string[];
    readonly student_ids?: readonly string[];
  };
  readonly schedule: ReadonlyArray<{
    readonly fee_head_id: string;
    readonly amount_paise: number;
    readonly due_date: string;
  }>;
  readonly fee_heads: readonly FeeHeadDTO[];
};

export type CreateFeePlanRequest = {
  readonly fee_heads: ReadonlyArray<{ readonly code: string; readonly label_key: string }>;
  readonly applicability: FeePlanDTO["applicability"];
  readonly schedule: ReadonlyArray<{
    readonly fee_head_code: string;
    readonly amount_paise: number;
    readonly due_date: string;
  }>;
  readonly version: number;
};

export type OverdueItemDTO = {
  readonly student_id: string;
  readonly charge_id: string;
  readonly amount_paise: number;
  readonly balance_paise: number;
  readonly due_date: string;
  readonly display_name: string | null;
};

const S1 = "1e06f5ad-b530-51fa-a3be-e1bd65fd230c";

/** Ledger statement and balance for one student. */
export async function fetchStatement(studentId = S1): Promise<FeeStatementDTO> {
  return request<FeeStatementDTO>(`${BASE}/fees/students/${studentId}/fee-statement`);
}

/** Overdue open charge balances. */
export async function fetchOverdue(
  query: { readonly as_of?: string; readonly cursor?: string } = {},
): Promise<Collection<OverdueItemDTO>> {
  return request<Collection<OverdueItemDTO>>(`${BASE}/fees/overdue`, { query });
}

/** Create a versioned fee plan with heads and schedule. */
export async function createFeePlan(body: CreateFeePlanRequest): Promise<FeePlanDTO> {
  return request<FeePlanDTO>(`${BASE}/fee-plans`, { method: "POST", body });
}

/** Record a manual payment and allocations. */
export async function postPayment(body: {
  readonly student_id: string;
  readonly amount_paise: number;
  readonly method: string;
  readonly reference?: string;
  readonly allocations: ReadonlyArray<{ readonly charge_id: string; readonly amount_paise: number }>;
  readonly idempotencyKey: string;
}): Promise<PaymentReceiptDTO> {
  return request<PaymentReceiptDTO>(`${BASE}/payments`, {
    method: "POST",
    body: {
      student_id: body.student_id,
      amount_paise: body.amount_paise,
      method: body.method,
      reference: body.reference ?? null,
      allocations: body.allocations,
    },
    headers: { "Idempotency-Key": body.idempotencyKey },
  });
}

/** Fetch a payment/receipt by id. */
export async function fetchPayment(paymentId: string): Promise<PaymentDTO> {
  return request<PaymentDTO>(`${BASE}/payments/${paymentId}`);
}

/** Post an approved concession credit against a charge. */
export async function postConcession(body: {
  readonly charge_id: string;
  readonly amount_paise: number;
  readonly reason: string;
  readonly source_key: string;
  readonly major: boolean;
}): Promise<Record<string, unknown>> {
  return request(`${BASE}/concessions`, { method: "POST", body });
}

export { S1 as DEFAULT_STUDENT };
