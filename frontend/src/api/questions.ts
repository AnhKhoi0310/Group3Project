import type { ApiClient } from "./client";

export type AnswerStatus = "answered" | "insufficient_evidence" | "declined";

export interface EvidenceReview {
  id: number;
  rating: number;
  text: string;
  reviewer_name: string | null;
  review_date: string | null;
  reviewer_avatar_url?: string | null;
  image_urls?: string[];
}

export interface QuestionAnswer {
  target_id: number;
  target_name: string;
  status: AnswerStatus;
  answer: string;
  reviews_used: number;
  reviews_total: number;
  evidence: EvidenceReview[];
}

export function askQuestion(
  api: ApiClient,
  targetId: string,
  question: string,
): Promise<QuestionAnswer> {
  return api.request<QuestionAnswer>(
    `/api/targets/${encodeURIComponent(targetId)}/questions`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    },
  );
}
