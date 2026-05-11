import type { BordereauDetail, BordereauImport } from "@/types";
import api from "./client";

export async function listBordereau(projectId: string): Promise<BordereauImport[]> {
  const { data } = await api.get<BordereauImport[]>(`/projects/${projectId}/bordereau`);
  return data;
}

export async function uploadBordereau(
  projectId: string,
  file: File,
  indice: string
): Promise<BordereauImport> {
  const form = new FormData();
  form.append("file", file);
  form.append("indice", indice);
  const { data } = await api.post<BordereauImport>(
    `/projects/${projectId}/bordereau/upload`,
    form,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return data;
}

export async function getBordereau(
  projectId: string,
  importId: string,
  page = 1,
  perPage = 50,
  sectionCode = "",
  search = ""
): Promise<BordereauDetail> {
  const { data } = await api.get<BordereauDetail>(
    `/projects/${projectId}/bordereau/${importId}`,
    {
      params: {
        page,
        per_page: perPage,
        section_code: sectionCode || undefined,
        search: search || undefined,
      },
    }
  );
  return data;
}

export async function updateBordereauIndice(
  projectId: string,
  importId: string,
  indice: string
): Promise<BordereauImport> {
  const form = new FormData();
  form.append("indice", indice);
  const { data } = await api.patch<BordereauImport>(
    `/projects/${projectId}/bordereau/${importId}/indice`,
    form,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return data;
}

export async function deleteBordereau(projectId: string, importId: string): Promise<void> {
  await api.delete(`/projects/${projectId}/bordereau/${importId}`);
}
