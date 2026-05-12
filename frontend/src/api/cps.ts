import type { CpsImport, CpsImportDetail } from "@/types";
import api from "./client";

export async function listCpsImports(projectId: string): Promise<CpsImport[]> {
  const { data } = await api.get<CpsImport[]>(`/projects/${projectId}/cps-imports`);
  return data;
}

export async function uploadCps(projectId: string, file: File): Promise<CpsImport> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post<CpsImport>(
    `/projects/${projectId}/cps-imports`,
    form,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return data;
}

export async function getCpsImport(
  projectId: string,
  importId: string
): Promise<CpsImportDetail> {
  const { data } = await api.get<CpsImportDetail>(
    `/projects/${projectId}/cps-imports/${importId}`
  );
  return data;
}

export async function deleteCpsImport(projectId: string, importId: string): Promise<void> {
  await api.delete(`/projects/${projectId}/cps-imports/${importId}`);
}
