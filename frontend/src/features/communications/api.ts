/**
 * Typed API surface for M11 communications.
 *
 * Shapes mirror contracts/M11/openapi.json.
 */

import { request } from "@shared/api/client";

const BASE = "/api/v1";

export type NoticeLocale = "en" | "ml";

export interface AudienceSelector {
  readonly kind: "section" | "person_ids";
  readonly section_id?: string;
  readonly person_ids?: readonly string[];
}

export interface Notice {
  readonly id: string;
  readonly school_id: string;
  readonly title: string;
  readonly body: string;
  readonly locale: NoticeLocale;
  readonly audience: AudienceSelector;
  readonly state: "draft" | "published";
  readonly version: number;
  readonly scheduled_at: string | null;
  readonly created_at: string;
  readonly updated_at: string;
  readonly audience_snapshot_id: string | null;
}

export interface AudienceSnapshot {
  readonly id: string;
  readonly notice_id: string;
  readonly recipient_ids: readonly string[];
  readonly created_at: string;
}

export interface Delivery {
  readonly id: string;
  readonly school_id: string;
  readonly recipient_ref: string;
  readonly channel: "in_app" | "sms";
  readonly dedupe_key: string;
  readonly payload_hash: string;
  readonly state: string;
  readonly provider_ref: string | null;
  readonly template_key: string;
  readonly locale: NoticeLocale;
  readonly version: number;
  readonly created_at: string;
  readonly updated_at: string;
  readonly attempts: readonly {
    readonly id: string;
    readonly attempted_at: string;
    readonly outcome: string;
  }[];
}

/** Create a draft notice. */
export async function createNotice(body: {
  readonly title: string;
  readonly body: string;
  readonly locale: NoticeLocale;
  readonly audience: AudienceSelector;
  readonly scheduled_at?: string | null;
}): Promise<Notice> {
  return request<Notice>(`${BASE}/notices`, { method: "POST", body });
}

/** Publish a draft and snapshot its audience. */
export async function publishNotice(
  noticeId: string,
  expectedVersion: number,
): Promise<{ readonly notice: Notice; readonly audience_snapshot: AudienceSnapshot }> {
  return request(`${BASE}/notices/${noticeId}/publish`, {
    method: "POST",
    body: { expected_version: expectedVersion },
  });
}

/** Enqueue a templated message delivery. */
export async function enqueueMessage(body: {
  readonly template_key: string;
  readonly recipient_ref: string;
  readonly locale: NoticeLocale;
  readonly variables: Record<string, string | number | boolean | null>;
  readonly channel: "in_app" | "sms";
  readonly dedupe_key: string;
}): Promise<Delivery> {
  return request<Delivery>(`${BASE}/messages`, { method: "POST", body });
}

/** Read one delivery with sanitized attempt history. */
export async function getDelivery(deliveryId: string): Promise<Delivery> {
  return request<Delivery>(`${BASE}/deliveries/${deliveryId}`);
}
