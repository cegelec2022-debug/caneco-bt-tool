import type { CableBookReport, CarnetParTableau } from "@/types";
import api from "./client";

export async function getCableBook(
  projectId: string,
  canecoExportId: string,
  filterRepereAval?: string
): Promise<CableBookReport> {
  const params = new URLSearchParams({ caneco_export_id: canecoExportId });
  if (filterRepereAval) params.set("repere_aval", filterRepereAval);
  const { data } = await api.get<CableBookReport>(
    `/projects/${projectId}/cable-book?${params.toString()}`
  );
  return data;
}

/** Carnet par tableau (style PDF CANECO). */
export async function getCableBookByTableau(
  projectId: string,
  canecoExportId: string,
  filterTableau?: string
): Promise<CarnetParTableau> {
  const params = new URLSearchParams({ caneco_export_id: canecoExportId });
  if (filterTableau) params.set("tableau", filterTableau);
  const { data } = await api.get<CarnetParTableau>(
    `/projects/${projectId}/cable-book/by-tableau?${params.toString()}`
  );
  return data;
}

export function buildCableBookExportUrl(
  projectId: string,
  canecoExportId: string,
  filterRepereAval?: string
): string {
  const params = new URLSearchParams({ caneco_export_id: canecoExportId });
  if (filterRepereAval) params.set("repere_aval", filterRepereAval);
  return `/projects/${projectId}/cable-book/export.xlsx?${params.toString()}`;
}

export async function downloadCableBookExcel(
  projectId: string,
  canecoExportId: string,
  filterRepereAval?: string
): Promise<{ blob: Blob; filename: string }> {
  const params = new URLSearchParams({ caneco_export_id: canecoExportId });
  if (filterRepereAval) params.set("repere_aval", filterRepereAval);
  const response = await api.get(
    `/projects/${projectId}/cable-book/export.xlsx?${params.toString()}`,
    { responseType: "blob" }
  );
  // Extract filename from Content-Disposition header
  const cd = response.headers["content-disposition"] as string | undefined;
  let filename = `carnet-cables.xlsx`;
  if (cd) {
    const match = cd.match(/filename="([^"]+)"/);
    if (match) filename = match[1];
  }
  return { blob: response.data as Blob, filename };
}
