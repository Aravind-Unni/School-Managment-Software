/**
 * Typed API surface for the demo module.
 *
 * The request and response shapes are taken from the GENERATED schema, which
 * comes from the module's approved OpenAPI. Hand-writing them would let the
 * client drift from the contract silently.
 */

import { request, walkPages, type Collection } from "@shared/api/client";
import type { components } from "./generated/schema";

export type Note = components["schemas"]["NoteResponse"];
export type NoteCollection = components["schemas"]["NoteCollectionResponse"];

const COLLECTION = "/api/demo/notes/";

/** Fetch one page of notes. */
export async function listNotes(
  options: { readonly cursor?: string; readonly pageSize?: number } = {},
): Promise<Collection<Note>> {
  const query: Record<string, string | number | undefined> = {};
  if (options.cursor !== undefined) query["cursor"] = options.cursor;
  if (options.pageSize !== undefined) query["page_size"] = options.pageSize;
  return request<Collection<Note>>(COLLECTION, { query });
}

/** Iterate every page of notes. */
export function walkNotes(pageSize?: number) {
  return walkPages<Note>(COLLECTION, pageSize === undefined ? {} : { pageSize });
}

/** Read one note. Throws ApiError with code object_inaccessible for a 404. */
export async function readNote(noteId: string): Promise<Note> {
  return request<Note>(`${COLLECTION}${noteId}/`);
}

/** Create a note about one person. */
export async function createNote(input: {
  readonly body: string;
  readonly subjectPersonId: string;
}): Promise<Note> {
  return request<Note>(COLLECTION, {
    method: "POST",
    body: { body: input.body, subject_person_id: input.subjectPersonId },
  });
}

/**
 * Update a note under optimistic concurrency.
 *
 * `expectedVersion` is mandatory. Omitting it would be a last-write-wins
 * overwrite, which the platform forbids; the server returns 409 on a mismatch.
 */
export async function updateNote(
  noteId: string,
  input: { readonly body: string; readonly expectedVersion: number },
): Promise<Note> {
  return request<Note>(`${COLLECTION}${noteId}/`, {
    method: "PATCH",
    body: { body: input.body, expected_version: input.expectedVersion },
  });
}
