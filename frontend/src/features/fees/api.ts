/** API helpers for M07 fees. */

export type BalanceDTO = {
  student_id: string | null;
  charged_paise: number;
  credited_paise: number;
  paid_paise: number;
  outstanding_paise: number;
  overdue_paise: number;
  credit_available_paise: number;
  as_of: string;
};

export type FeeStatementDTO = {
  student_id: string;
  as_of: string;
  entries: Array<{
    entry_type: string;
    id: string;
    amount_paise: number;
    posted_at: string;
    description_key: string;
  }>;
  balance: BalanceDTO;
  student_display_name: string | null;
};

export type PaymentReceiptDTO = {
  payment: {
    id: string;
    number: string;
    amount_paise: number;
    method: string;
    version: number;
  };
  balance: BalanceDTO;
};

const S1 = "1e06f5ad-b530-51fa-a3be-e1bd65fd230c";

export async function fetchStatement(studentId = S1): Promise<FeeStatementDTO> {
  const res = await fetch(`/api/v1/fees/students/${studentId}/fee-statement`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error(`statement_failed_${res.status}`);
  return (await res.json()) as FeeStatementDTO;
}

export async function fetchOverdue(): Promise<{ items: Array<Record<string, unknown>> }> {
  const res = await fetch(`/api/v1/fees/overdue`, { credentials: "include" });
  if (!res.ok) throw new Error(`overdue_failed_${res.status}`);
  return (await res.json()) as { items: Array<Record<string, unknown>> };
}

export async function postPayment(body: {
  student_id: string;
  amount_paise: number;
  method: string;
  reference?: string;
  allocations: Array<{ charge_id: string; amount_paise: number }>;
  idempotencyKey: string;
}): Promise<PaymentReceiptDTO> {
  const res = await fetch(`/api/v1/payments`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": body.idempotencyKey,
    },
    body: JSON.stringify({
      student_id: body.student_id,
      amount_paise: body.amount_paise,
      method: body.method,
      reference: body.reference ?? null,
      allocations: body.allocations,
    }),
  });
  if (!res.ok) throw new Error(`payment_failed_${res.status}`);
  return (await res.json()) as PaymentReceiptDTO;
}

export async function fetchPayment(paymentId: string): Promise<Record<string, unknown>> {
  const res = await fetch(`/api/v1/payments/${paymentId}`, {
    credentials: "include",
  });
  if (!res.ok) {
    throw new Error(`payment_get_failed_${res.status}`);
  }
  return (await res.json()) as Record<string, unknown>;
}

export { S1 as DEFAULT_STUDENT };
