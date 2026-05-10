import type { CanecoExport, CanecoExportDetail } from "@/types";
import api from "./client";

export async function listCaneco(projectId: string): Promise<CanecoExport[]> {
  const { data } = await api.get<CanecoExport[]>(`/projects/${projectId}/caneco`);
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
    `/projects/${projectId}/caneco/upload`,
    form,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return data;
}

export async function getCaneco(
  projectId: string,
  exportId: string,
  page = 1,
  perPage = 50,
  search = ""
): Promise<CanecoExportDetail> {
  const { data } = await api.get<CanecoExportDetail>(
    `/projects/${projectId}/caneco/${exportId}`,
    { params: { page, per_page: perPage, search: search || undefined } }
  );
  return data;
}

export async function updateCanecoIndice(
  projectId: string,
  exportId: string,
  indice: string
): Promise<CanecoExport> {
  const form = new FormData();
  form.append("indice", indice);
  const { data } = await api.patch<CanecoExport>(
    `/projects/${projectId}/caneco/${exportId}/indice`,
    form,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return data;
}

export async function downloadCanecoExcel(
  projectId: string,
  exportId: string,
  indice: string
): Promise<void> {
  const response = await api.get(
    `/projects/${projectId}/caneco/${exportId}/export-excel`,
    { responseType: "blob" }
  );
  const url = URL.createObjectURL(new Blob([response.data as BlobPart]));
  const a = document.createElement("a");
  a.href = url;
  a.download = `CANECO_Indice_${indice}.xlsx`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export async function deleteCaneco(projectId: string, exportId: string): Promise<void> {
  await api.delete(`/projects/${projectId}/caneco/${exportId}`);
}
