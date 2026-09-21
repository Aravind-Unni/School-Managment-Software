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

/** List action codes the caller holds (navigation only). */
export async function listCapabilities(): Promise<{ actions: string[] }> {
  return call<{ actions: string[] }>("/auth/capabilities");
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

/** An account as returned by the account-administration endpoints. */
export interface ManagedAccount {
  readonly id: string;
  readonly login_name: string;
  readonly display_name: string;
  readonly person_id: string | null;
  readonly active: boolean;
  readonly version: number;
  readonly role_ids: readonly string[];
  readonly has_active_factor: boolean;
  readonly two_factor_required: boolean;
  /** Present only on create and password reset, and only that once. */
  readonly temporary_password?: string | null;
}

/** Every role in the school (small collection). */
export async function listAllRoles(): Promise<Role[]> {
  const roles: Role[] = [];
  let cursor: string | undefined;
  do {
    const page = await listRoles(cursor);
    roles.push(...page.items);
    cursor = page.next_cursor ?? undefined;
  } while (cursor !== undefined);
  return roles;
}

/** Create a login; returns a one-time temporary password when none was given. */
export async function createAccount(input: {
  readonly loginName: string;
  readonly displayName: string;
  readonly personId: string | null;
  readonly roleIds: readonly string[];
}): Promise<ManagedAccount> {
  return call<ManagedAccount>("/accounts", {
    method: "POST",
    body: {
      login_name: input.loginName,
      display_name: input.displayName,
      person_id: input.personId,
      role_ids: input.roleIds,
    },
  });
}

/** Replace an account's roles. Signs the account out everywhere. */
export async function replaceAccountRoles(
  accountId: string,
  input: { readonly roleIds: readonly string[]; readonly expectedVersion: number },
): Promise<ManagedAccount> {
  return call<ManagedAccount>(`/accounts/${accountId}/roles`, {
    method: "PUT",
    body: { role_ids: input.roleIds, expected_version: input.expectedVersion },
  });
}

/** Activate or deactivate an account. */
export async function setAccountActive(
  accountId: string,
  input: { readonly active: boolean; readonly expectedVersion: number },
): Promise<ManagedAccount> {
  return call<ManagedAccount>(
    `/accounts/${accountId}/${input.active ? "activate" : "deactivate"}`,
    { method: "POST", body: { expected_version: input.expectedVersion } },
  );
}

/** Issue a new temporary password for an account. */
export async function resetAccountPassword(accountId: string): Promise<ManagedAccount> {
  return call<ManagedAccount>(`/accounts/${accountId}/reset-password`, { method: "POST" });
}

/** Change one's own password. Other sessions are signed out. */
export async function changeOwnPassword(input: {
  readonly currentPassword: string;
  readonly newPassword: string;
}): Promise<void> {
  await call<unknown>("/auth/password", {
    method: "POST",
    body: { current_password: input.currentPassword, new_password: input.newPassword },
  });
}

/** Suggest a login name from a display name: "Anita Nair" -> "anita.nair". */
export function suggestLoginName(displayName: string): string {
  return displayName
    .normalize("NFKD")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ".")
    .replace(/^\.+|\.+$/g, "")
    .slice(0, 40);
}
