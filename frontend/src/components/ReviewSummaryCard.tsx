import { useEffect, useState } from "react";
import { ApiError, type ApiClient } from "../api/client";
import { getReviewSummary, type ReviewSummary } from "../api/reviews";
import ErrorMessage from "./ErrorMessage";

const UNEXPECTED = "We couldn't load the review summary. Please try again.";
const STAR_LEVELS = [5, 4, 3, 2, 1] as const;

interface Props {
  api: ApiClient;
  targetId: string;
  targetName: string;
  refreshKey: number;
}

export default function ReviewSummaryCard({
  api,
  targetId,
  targetName,
  refreshKey,
}: Props) {
  const [summary, setSummary] = useState<ReviewSummary | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setError("");

    getReviewSummary(api, targetId)
      .then((data) => {
        if (active) setSummary(data);
      })
      .catch((caught: unknown) => {
        if (!active) return;
        setError(caught instanceof ApiError ? caught.message : UNEXPECTED);
      });

    return () => {
      active = false;
    };
  }, [api, targetId, refreshKey]);

  return (
    <section
      aria-labelledby="review-summary-heading"
      className="space-y-4 rounded-lg border border-slate-200 bg-white p-6"
    >
      <h2 id="review-summary-heading" className="text-lg font-semibold">
        Review summary for {targetName}
      </h2>
      {error && <ErrorMessage message={error} />}
      {!error && !summary && (
        <p className="text-sm text-slate-600">Loading review summary…</p>
      )}
      {summary && (
        <>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Ingested reviews
              </p>
              <p
                data-testid="summary-review-count"
                className="mt-1 text-2xl font-semibold text-slate-900"
              >
                {summary.review_count}
              </p>
            </div>
            <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Average rating
              </p>
              <p
                data-testid="summary-average-rating"
                className="mt-1 text-2xl font-semibold text-slate-900"
              >
                {summary.average_rating !== null
                  ? `${summary.average_rating.toFixed(1)} / 5`
                  : "No ratings yet"}
              </p>
            </div>
          </div>
          <div>
            <h3 className="text-sm font-medium text-slate-700">
              Rating distribution
            </h3>
            <ul className="mt-2 space-y-1 text-sm text-slate-700">
              {STAR_LEVELS.map((star) => {
                const count = summary.rating_distribution[String(star)] ?? 0;
                return (
                  <li
                    key={star}
                    className="flex items-center justify-between border-b border-slate-100 py-1 last:border-b-0"
                  >
                    <span>{star} ★</span>
                    <span className="font-medium">{count}</span>
                  </li>
                );
              })}
            </ul>
          </div>
        </>
      )}
    </section>
  );
}
