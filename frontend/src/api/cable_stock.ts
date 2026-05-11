import type { CableStockReport, CableStockUpsert } from "@/types";
import api from "./client";

export async function getCableStock(projectId: string): Promise<CableStockReport> {
  const { data } = await api.get<CableStockReport>(
    `/projects/${projectId}/cable-stock`
  );
  return data;
}

export async function upsertCableStock(
  projectId: string,
  payload: CableStockUpsert
): Promise<CableStockReport> {
  const { data } = await api.put<CableStockReport>(
    `/projects/${projectId}/cable-stock`,
    payload
  );
  return data;
}

export async function deleteCableStockItem(
  projectId: string,
  itemId: string
): Promise<void> {
  await api.delete(`/projects/${projectId}/cable-stock/${itemId}`);
}
