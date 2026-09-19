/**
 * Typed API surface for M01.
 *
 * Request and response shapes come from the GENERATED schema, which is produced
 * from the module's approved OpenAPI. Hand-writing them would let the client drift
 * from the contract silently.
 *
 * The CSRF token is echoed from its readable cookie into a header on every unsafe
 * request -- the double-submit pattern the backend enforces.
 */

import { request, type Collection } from "@shared/api/client";
import type { components } from "./generated/schema";

type Schemas = components["schemas"];

export type Challenge = Schemas["ChallengeResponse"];
export type Authenticated = Schemas["AuthenticatedResponse"];
export type EnrolStart = Schemas["EnrolStartResponse"];
export type RecoveryCodes = Schemas["RecoveryCodesResponse"];
export type SessionRecord = Schemas["SessionResponse"];
export type Role = Schemas["RoleResponse"];
export type Account = Schemas["AccountResponse"];
export type RecoveryCase = Schemas["RecoveryCaseResponse"];

const BASE = "/api/v1";
const CSRF_COOKIE = "school_csrf";

/** Read the CSRF cookie. Returns null when absent (no session yet). */
function csrfToken(): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${CSRF_COOKIE}=([^;]*)`));
  return match?.[1] ? decodeURIComponent(match[1]) : null;
}

/**
 * Perform an M01 call, attaching the CSRF header when a token exists.
 *
 * Login has no token yet and needs none: there is no session to ride, so there is
 * nothing for a cross-site request to forge with.
 */
async function call<Result>(
  path: string,
  options: { method?: "GET" | "POST" | "PUT"; body?: unknown; query?: Record<string, string | number | undefined> } = {},
): Promise<Result> {
  const token = csrfToken();
  const headers: Record<string, string> = {};
  if (token !== null) headers["X-CSRF-Token"] = token;
  return request<Result>(`${BASE}${path}`, { ...options, headers });
}

/** Begin authentication. Returns a challenge, never a session. */
export async function login(input: { loginName: string; password: string }): Promise<Challenge> {
  return call<Challenge>("/auth/login", {
    method: "POST",
    body: { login_name: input.loginName, password: input.password },
  });
}

/** Complete a challenge with a TOTP code. */
export async function verifyTotp(input: { challengeId: string; code: string }): Promise<Authenticated> {
  return call<Authenticated>("/auth/2fa/verify", {
    method: "POST",
    body: { challenge_id: input.challengeId, code: input.code },
  });
}

/**
 * Begin enrolment.
 *
 * `challengeId` is supplied for a FIRST enrolment, where the account has no session
 * yet because its role requires a factor it does not have.
 */
export async function startEnrolment(input: {
  password: string;
  challengeId?: string;
}): Promise<EnrolStart> {
  return call<EnrolStart>("/auth/2fa/enroll", {
    method: "POST",
    body: { password: input.password, challenge_id: input.challengeId ?? null },
  });
}

/** Activate the pending factor and receive recovery codes once. */
export async function confirmEnrolment(input: {
  factorId: string;
  code: string;
  password: string;
  challengeId?: string;
}): Promise<RecoveryCodes> {
  return call<RecoveryCodes>("/auth/2fa/confirm", {
    method: "POST",
    body: {
      factor_id: input.factorId,
      code: input.code,
      password: input.password,
      challenge_id: input.challengeId ?? null,
    },
  });
}

/** Sign in with a single-use recovery code. */
export async function recover(input: {
  challengeId: string;
  recoveryCode: string;
}): Promise<Authenticated> {
  return call<Authenticated>("/auth/2fa/recover", {
    method: "POST",
    body: { challenge_id: input.challengeId, recovery_code: input.recoveryCode },
  });
}

/** Open a lost-device identity-verification case. */
export async function requestFactorReset(reason: string): Promise<RecoveryCase> {
  return call<RecoveryCase>("/auth/factor/reset-requests", { method: "POST", body: { reason } });
}

/** Describe the calling session. */
export async function currentSession(): Promise<Authenticated> {
  return call<Authenticated>("/auth/session");
}

/** Revoke the current session. */
export async function logout(): Promise<void> {
  await call<{ revoked: boolean }>("/auth/logout", { method: "POST" });
}

/** List the caller's own sessions. */
export async function listSessions(cursor?: string): Promise<Collection<SessionRecord>> {
  return call<Collection<SessionRecord>>("/sessions", { query: cursor ? { cursor } : {} });
}

/** Revoke one of the caller's own sessions. */
export async function revokeSession(sessionId: string): Promise<SessionRecord> {
  return call<SessionRecord>(`/sessions/${sessionId}/revoke`, { method: "POST" });
}

/** List roles in the caller's school. */
export async function listRoles(cursor?: string): Promise<Collection<Role>> {
  return call<Collection<Role>>("/roles", { query: cursor ? { cursor } : {} });
}

/** Replace a role's grants under optimistic concurrency. */
export async function replaceGrants(
  roleId: string,
  input: { name: string; grants: Role["grants"]; expectedVersion: number },
): Promise<Role> {
  return call<Role>(`/roles/${roleId}/grants`, {
    method: "PUT",
    body: { name: input.name, grants: input.grants, expected_version: input.expectedVersion },
  });
}

/** List accounts. The protected business endpoint. */
export async function listAccounts(cursor?: string): Promise<Collection<Account>> {
  return call<Collection<Account>>("/accounts", { query: cursor ? { cursor } : {} });
}
