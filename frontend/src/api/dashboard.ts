import type { DashboardSummary } from "@/types";
import api from "./client";

export async function getDashboardSummary(): Promise<DashboardSummary> {
  const { data } = await api.get<DashboardSummary>("/dashboard/summary");
  return data;
}
