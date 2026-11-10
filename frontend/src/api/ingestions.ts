import type { ApiClient } from "./client";

export interface IngestionAttempt {
  attempt_id: number;
  target_id: number;
  status: "processing" | "succeeded" | "failed";
  reviews_found: number;
  reviews_skipped: number;
  failure_category: string | null;
  started_at: string;
  completed_at: string | null;
}

export type IngestionResult = IngestionAttempt;

export function startIngestion(
  api: ApiClient,
  targetId: number,
): Promise<IngestionResult> {
  return api.request<IngestionResult>(`/api/targets/${targetId}/ingestions`, {
    method: "POST",
  });
}

export function getLatestIngestion(
  api: ApiClient,
  targetId: string,
): Promise<IngestionAttempt | null> {
  return api.request<IngestionAttempt | null>(
    `/api/targets/${encodeURIComponent(targetId)}/ingestions/latest`,
  );
}
