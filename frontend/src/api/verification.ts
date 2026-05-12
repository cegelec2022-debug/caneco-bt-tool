import type {
  Gap,
  GapStatus,
  GapStatusUpdate,
  VerificationRun,
  VerificationRunCreate,
  VerificationRunDetail,
} from "@/types";
import api from "./client";

export async function createVerificationRun(
  projectId: string,
  payload: VerificationRunCreate
): Promise<VerificationRun> {
  const { data } = await api.post<VerificationRun>(
    `/projects/${projectId}/verification-runs`,
    payload
  );
  return data;
}

export async function listVerificationRuns(projectId: string): Promise<VerificationRun[]> {
  const { data } = await api.get<VerificationRun[]>(
    `/projects/${projectId}/verification-runs`
  );
  return data;
}

export async function getVerificationRun(
  projectId: string,
  runId: string
): Promise<VerificationRunDetail> {
  const { data } = await api.get<VerificationRunDetail>(
    `/projects/${projectId}/verification-runs/${runId}`
  );
  return data;
}

export async function deleteVerificationRun(
  projectId: string,
  runId: string
): Promise<void> {
  await api.delete(`/projects/${projectId}/verification-runs/${runId}`);
}

export async function listGaps(
  projectId: string,
  runId: string,
  filters?: { severity?: string; status?: GapStatus; code?: string }
): Promise<Gap[]> {
  const params = new URLSearchParams();
  if (filters?.severity) params.set("severity", filters.severity);
  if (filters?.status) params.set("status", filters.status);
  if (filters?.code) params.set("code", filters.code);
  const qs = params.toString() ? `?${params.toString()}` : "";
  const { data } = await api.get<Gap[]>(
    `/projects/${projectId}/verification-runs/${runId}/gaps${qs}`
  );
  return data;
}

export async function updateGapStatus(
  projectId: string,
  runId: string,
  gapId: string,
  payload: GapStatusUpdate
): Promise<Gap> {
  const { data } = await api.patch<Gap>(
    `/projects/${projectId}/verification-runs/${runId}/gaps/${gapId}`,
    payload
  );
  return data;
}
