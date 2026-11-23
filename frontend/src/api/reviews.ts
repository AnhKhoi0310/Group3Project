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
  reviewer_avatar_url?: string | null;
  image_urls?: string[];
}

export function listReviews(
  api: ApiClient,
  targetId: string,
): Promise<Review[]> {
  return api.request<Review[]>(
    `/api/targets/${encodeURIComponent(targetId)}/reviews`,
  );
}

export interface ReviewSummary {
  target_id: number;
  target_name: string;
  review_count: number;
  average_rating: number | null;
  rating_distribution: Record<string, number>;
}

export function getReviewSummary(
  api: ApiClient,
  targetId: string,
): Promise<ReviewSummary> {
  return api.request<ReviewSummary>(
    `/api/targets/${encodeURIComponent(targetId)}/summary`,
  );
}
