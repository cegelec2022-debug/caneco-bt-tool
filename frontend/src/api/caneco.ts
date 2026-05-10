import type { CanecoExport, CanecoExportDetail } from "@/types";
import api from "./client";

export async function listCaneco(projectId: string): Promise<CanecoExport[]> {
  const { data } = await api.get<CanecoExport[]>(`/api/projects/${projectId}/caneco`);
  return data;
}

export async function uploadCaneco(
  projectId: string,
  file: File,
  indice: string
): Promise<CanecoExport> {
  const form = new FormData();
  form.append("file", file);
  form.append("indice", indice);
  const { data } = await api.post<CanecoExport>(
    `/api/projects/${projectId}/caneco/upload`,
    form,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return data;
}

export async function getCaneco(
  projectId: string,
  exportId: string,
  page = 1,
  perPage = 50
): Promise<CanecoExportDetail> {
  const { data } = await api.get<CanecoExportDetail>(
    `/api/projects/${projectId}/caneco/${exportId}`,
    { params: { page, per_page: perPage } }
  );
  return data;
}

export async function deleteCaneco(projectId: string, exportId: string): Promise<void> {
  await api.delete(`/api/projects/${projectId}/caneco/${exportId}`);
}
