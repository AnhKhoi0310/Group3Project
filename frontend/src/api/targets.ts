import type { ApiClient } from "./client";

export interface AnalysisTarget {
  id: number;
  name: string;
  platform: string;
  source_url: string;
  created_at: string;
}

export interface NewTarget {
  name: string;
  source_url: string;
}

export function createTarget(
  api: ApiClient,
  input: NewTarget,
): Promise<AnalysisTarget> {
  return api.request<AnalysisTarget>("/api/targets", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export function listTargets(api: ApiClient): Promise<AnalysisTarget[]> {
  return api.request<AnalysisTarget[]>("/api/targets");
}

export function getTarget(
  api: ApiClient,
  targetId: string,
): Promise<AnalysisTarget> {
  return api.request<AnalysisTarget>(
    `/api/targets/${encodeURIComponent(targetId)}`,
  );
}
