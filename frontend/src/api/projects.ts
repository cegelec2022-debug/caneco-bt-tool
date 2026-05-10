import type { Project, ProjectCreate, ProjectUpdate } from "@/types";
import apiClient from "./client";

export async function listProjects(): Promise<Project[]> {
  const { data } = await apiClient.get<Project[]>("/projects/");
  return data;
}

export async function getProject(id: string): Promise<Project> {
  const { data } = await apiClient.get<Project>(`/projects/${id}`);
  return data;
}

export async function createProject(payload: ProjectCreate): Promise<Project> {
  const { data } = await apiClient.post<Project>("/projects/", payload);
  return data;
}

export async function updateProject(id: string, payload: ProjectUpdate): Promise<Project> {
  const { data } = await apiClient.patch<Project>(`/projects/${id}`, payload);
  return data;
}

export async function deleteProject(id: string): Promise<void> {
  await apiClient.delete(`/projects/${id}`);
}
