import type { ApiClient } from "./client";

export interface Review {
  id: number;
  target_id: number;
  source_review_id: string | null;
  source_platform: string;
  reviewer_name: string | null;
  rating: number;
  text: string;
  review_date: string | null;
  created_at: string;
}

export function listReviews(
  api: ApiClient,
  targetId: string,
): Promise<Review[]> {
  return api.request<Review[]>(
    `/api/targets/${encodeURIComponent(targetId)}/reviews`,
  );
}
