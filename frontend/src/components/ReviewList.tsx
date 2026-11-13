import { useEffect, useState } from "react";
import { ApiError, type ApiClient } from "../api/client";
import { listReviews, type Review } from "../api/reviews";
import Button from "./Button";
import ErrorMessage from "./ErrorMessage";

const INITIAL_COUNT = 10;
const UNEXPECTED = "We couldn't load the saved reviews. Please try again.";

function Stars({ rating }: { rating: number }) {
  const filled = Math.max(0, Math.min(5, Math.round(rating)));
  return (
    <span
      role="img"
      aria-label={`${rating} out of 5 stars`}
      className="text-amber-500"
    >
      {"★".repeat(filled)}
      <span className="text-slate-300">{"★".repeat(5 - filled)}</span>
    </span>
  );
}

interface Props {
  api: ApiClient;
  targetId: string;
  /** Change this value to reload, for example after a collection finishes. */
  refreshKey: number;
}

/** Reviews already saved for one target, loaded from the backend. */
export default function ReviewList({ api, targetId, refreshKey }: Props) {
  const [reviews, setReviews] = useState<Review[] | null>(null);
  const [error, setError] = useState("");
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    let active = true;
    setError("");

    listReviews(api, targetId)
      .then((items) => {
        if (active) setReviews(Array.isArray(items) ? items : []);
      })
      .catch((caught: unknown) => {
        if (!active) return;
        setError(caught instanceof ApiError ? caught.message : UNEXPECTED);
      });

    return () => {
      active = false;
    };
  }, [api, targetId, refreshKey]);

  const visible = showAll ? reviews : reviews?.slice(0, INITIAL_COUNT);

  return (
    <section
      aria-labelledby="saved-reviews"
      className="space-y-4 rounded-lg border border-slate-200 bg-white p-6"
    >
      <h2 id="saved-reviews" className="text-lg font-semibold">
        Saved reviews{reviews ? ` (${reviews.length})` : ""}
      </h2>
      {error && <ErrorMessage message={error} />}
      {!error && reviews === null && (
        <p className="text-sm text-slate-600">Loading saved reviews…</p>
      )}
      {reviews?.length === 0 && (
        <p className="text-sm text-slate-600">
          No reviews saved yet. Use Collect reviews to get them from the source.
        </p>
      )}
      {visible && visible.length > 0 && (
        <ul className="divide-y divide-slate-200">
          {visible.map((review) => (
            <li key={review.id} className="space-y-1 py-3">
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
                <Stars rating={review.rating} />
                <span className="font-medium text-slate-800">
                  {review.reviewer_name ?? "Anonymous"}
                </span>
                {review.review_date && (
                  <span className="text-slate-500">{review.review_date}</span>
                )}
              </div>
              <p className="whitespace-pre-line text-slate-700">
                {review.text}
              </p>
            </li>
          ))}
        </ul>
      )}
      {reviews && reviews.length > INITIAL_COUNT && (
        <Button onClick={() => setShowAll((value) => !value)}>
          {showAll ? "Show fewer" : `Show all ${reviews.length} reviews`}
        </Button>
      )}
    </section>
  );
}
