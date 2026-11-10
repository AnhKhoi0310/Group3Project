import type { ApiClient } from "./client";

export interface IngestionResult {
  target_id: number;
  reviews_found: number;
  reviews_skipped: number;
}

export function startIngestion(
  api: ApiClient,
  targetId: number,
): Promise<IngestionResult> {
  return api.request<IngestionResult>(`/api/targets/${targetId}/ingestions`, {
    method: "POST",
  });
}
