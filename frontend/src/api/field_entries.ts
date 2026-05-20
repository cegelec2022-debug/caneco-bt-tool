import type { FieldEntry, FieldEntryUpsert } from "@/types";
import api from "./client";

/** Cree ou met a jour la saisie chantier d'un depart (idempotent). */
export async function upsertFieldEntry(
  projectId: string,
  canecoLineId: string,
  payload: FieldEntryUpsert
): Promise<FieldEntry> {
  const { data } = await api.put<FieldEntry>(
    `/projects/${projectId}/field-entries/${canecoLineId}`,
    payload
  );
  return data;
}

/** Supprime la saisie chantier d'un depart. */
export async function deleteFieldEntry(
  projectId: string,
  canecoLineId: string
): Promise<void> {
  await api.delete(`/projects/${projectId}/field-entries/${canecoLineId}`);
}

/** Liste toutes les saisies chantier d'un projet. */
export async function listFieldEntries(projectId: string): Promise<FieldEntry[]> {
  const { data } = await api.get<FieldEntry[]>(
    `/projects/${projectId}/field-entries`
  );
  return data;
}
