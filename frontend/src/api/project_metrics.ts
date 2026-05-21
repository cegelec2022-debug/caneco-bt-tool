import type { ProjectMetrics } from "@/types";
import api from "./client";

/** Source unique des KPI projet (Tableaux, Saisie chantier, Dashboard). */
export async function getProjectMetrics(projectId: string): Promise<ProjectMetrics> {
  const { data } = await api.get<ProjectMetrics>(`/projects/${projectId}/metrics`);
  return data;
}
