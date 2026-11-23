import { useEffect, useId, useMemo, useRef, useState } from "react";
import { ApiError, type ApiClient } from "../api/client";
import { listReviews, type Review } from "../api/reviews";
import Avatar from "./Avatar";
import ErrorMessage from "./ErrorMessage";
import PhotoLightbox, { type Photo } from "./PhotoLightbox";
import Stars from "./Stars";

const THUMBNAILS = 4;
const HIGHLIGHT_MS = 2400;
const UNEXPECTED = "We couldn't load the saved reviews. Please try again.";
export const FOCUS_REVIEW_EVENT = "reviewlens:focus-review";

type SortKey = "newest" | "highest" | "lowest" | "photos";

const SORTS: Record<SortKey, string> = {
  newest: "Newest first",
  highest: "Highest rating",
  lowest: "Lowest rating",
  photos: "Most photos",
};

/** Ask the review list to scroll to one review and highlight it. */
export function focusReview(reviewId: number): void {
  window.dispatchEvent(
    new CustomEvent<number>(FOCUS_REVIEW_EVENT, { detail: reviewId }),
  );
}

interface Props {
  api: ApiClient;
  targetId: string;
  /** Change this value to reload, for example after a collection finishes. */
  refreshKey: number;
}

interface OpenPhotos {
  photos: Photo[];
  index: number;
}

/** A review's photos as small buttons that open the full-size view. */
export function ReviewPhotos({
  review,
  onOpen,
}: {
  review: Pick<Review, "image_urls" | "reviewer_name" | "rating">;
  onOpen: (photos: Photo[], index: number) => void;
}) {
  const urls = review.image_urls ?? [];
  if (urls.length === 0) return null;
  const by = review.reviewer_name ?? "A reviewer";
  const photos = urls.map((url) => ({
    url,
    caption: `${by}, ${review.rating} out of 5`,
  }));
  const shown = photos.slice(0, THUMBNAILS);
  const extra = photos.length - shown.length;

  return (
    <ul className="flex flex-wrap gap-2 pt-1">
      {shown.map((photo, index) => (
        <li key={photo.url}>
          <button
            type="button"
            onClick={() => onOpen(photos, index)}
            aria-label={`Open photo ${index + 1} of ${photos.length} from ${by}`}
            className="group relative block h-16 w-16 overflow-hidden rounded-md bg-slate-100 focus-visible:outline-2 focus-visible:outline-indigo-600"
          >
            <img
              src={photo.url}
              alt=""
              loading="lazy"
              referrerPolicy="no-referrer"
              className="h-full w-full object-cover transition duration-200 group-hover:scale-110"
            />
            {index === shown.length - 1 && extra > 0 && (
              <span className="absolute inset-0 flex items-center justify-center bg-slate-900/60 text-sm font-semibold text-white">
                +{extra}
              </span>
            )}
          </button>
        </li>
      ))}
    </ul>
  );
}

/** Wraps each case-insensitive match of the search in a highlight. */
export function Highlight({ text, query }: { text: string; query: string }) {
  const term = query.trim();
  if (!term) return <>{text}</>;
  const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const parts = text.split(new RegExp(`(${escaped})`, "gi"));
  return (
    <>
      {parts.map((part, index) =>
        part.toLowerCase() === term.toLowerCase() ? (
          <mark key={index} className="rounded bg-amber-200 px-0.5">
            {part}
          </mark>
        ) : (
          part
        ),
      )}
    </>
  );
}

function sortReviews(reviews: Review[], sort: SortKey): Review[] {
  const copy = [...reviews];
  if (sort === "highest") copy.sort((a, b) => b.rating - a.rating);
  else if (sort === "lowest") copy.sort((a, b) => a.rating - b.rating);
  else if (sort === "photos") {
    copy.sort(
      (a, b) => (b.image_urls?.length ?? 0) - (a.image_urls?.length ?? 0),
    );
  }
  return copy; // "newest" keeps the server's newest-first order
}

/**
 * Explore the reviews saved for one target: search, filter by stars, sort,
 * and scroll within the panel. Other components can jump to a review with
 * focusReview(id).
 */
export default function ReviewList({ api, targetId, refreshKey }: Props) {
  const searchId = useId();
  const sortId = useId();
  const [reviews, setReviews] = useState<Review[] | null>(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [stars, setStars] = useState<number | null>(null);
  const [sort, setSort] = useState<SortKey>("newest");
  const [open, setOpen] = useState<OpenPhotos | null>(null);
  const [focused, setFocused] = useState<number | null>(null);
  const items = useRef(new Map<number, HTMLLIElement>());

  useEffect(() => {
    let active = true;
    setError("");

    listReviews(api, targetId)
      .then((data) => {
        if (active) setReviews(Array.isArray(data) ? data : []);
      })
      .catch((caught: unknown) => {
        if (!active) return;
        setError(caught instanceof ApiError ? caught.message : UNEXPECTED);
      });

    return () => {
      active = false;
    };
  }, [api, targetId, refreshKey]);

  // Jump requests from the chat: clear filters that might hide the review.
  useEffect(() => {
    function onFocus(event: Event) {
      const id = (event as CustomEvent<number>).detail;
      setQuery("");
      setStars(null);
      setFocused(id);
    }
    window.addEventListener(FOCUS_REVIEW_EVENT, onFocus);
    return () => window.removeEventListener(FOCUS_REVIEW_EVENT, onFocus);
  }, []);

  useEffect(() => {
    if (focused === null) return;
    items.current
      .get(focused)
      ?.scrollIntoView?.({ behavior: "smooth", block: "center" });
    const timer = window.setTimeout(() => setFocused(null), HIGHLIGHT_MS);
    return () => window.clearTimeout(timer);
  }, [focused]);

  const counts = useMemo(() => {
    const result: Record<number, number> = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };
    for (const review of reviews ?? []) {
      const star = Math.max(1, Math.min(5, Math.round(review.rating)));
      result[star] += 1;
    }
    return result;
  }, [reviews]);

  const visible = useMemo(() => {
    const term = query.trim().toLowerCase();
    const filtered = (reviews ?? []).filter((review) => {
      if (stars !== null && Math.round(review.rating) !== stars) return false;
      if (!term) return true;
      return (
        review.text.toLowerCase().includes(term) ||
        (review.reviewer_name ?? "").toLowerCase().includes(term)
      );
    });
    return sortReviews(filtered, sort);
  }, [reviews, query, stars, sort]);

  const total = reviews?.length ?? 0;
  const filtering = query.trim() !== "" || stars !== null;

  function clearFilters() {
    setQuery("");
    setStars(null);
  }

  const chip = (active: boolean) =>
    `rounded-full border px-2.5 py-1 text-xs font-medium transition ${
      active
        ? "border-indigo-600 bg-indigo-600 text-white"
        : "border-slate-300 bg-white text-slate-700 hover:border-indigo-300 hover:bg-indigo-50"
    }`;

  return (
    <section
      aria-labelledby="saved-reviews"
      className="flex flex-col rounded-lg border border-slate-200 bg-white"
    >
      <div className="space-y-3 border-b border-slate-200 p-6 pb-4">
        <h2 id="saved-reviews" className="text-lg font-semibold">
          Saved reviews{reviews ? ` (${reviews.length})` : ""}
        </h2>

        {total > 0 && (
          <>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
              <div className="flex-1">
                <label htmlFor={searchId} className="block text-sm font-medium">
                  Search reviews
                </label>
                <input
                  id={searchId}
                  type="search"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Try a word like crust, wait or price"
                  className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label htmlFor={sortId} className="block text-sm font-medium">
                  Sort by
                </label>
                <select
                  id={sortId}
                  value={sort}
                  onChange={(event) => setSort(event.target.value as SortKey)}
                  className="mt-1 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
                >
                  {Object.entries(SORTS).map(([key, label]) => (
                    <option key={key} value={key}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div
              role="group"
              aria-label="Filter by rating"
              className="flex flex-wrap gap-1.5"
            >
              <button
                type="button"
                aria-pressed={stars === null}
                onClick={() => setStars(null)}
                className={chip(stars === null)}
              >
                All ({total})
              </button>
              {[5, 4, 3, 2, 1].map((star) => (
                <button
                  key={star}
                  type="button"
                  aria-pressed={stars === star}
                  aria-label={`${star}-star reviews (${counts[star]})`}
                  disabled={counts[star] === 0}
                  onClick={() => setStars(stars === star ? null : star)}
                  className={`${chip(stars === star)} disabled:cursor-not-allowed disabled:opacity-40`}
                >
                  {star}★ {counts[star]}
                </button>
              ))}
            </div>

            <p aria-live="polite" className="text-xs text-slate-500">
              Showing {visible.length} of {total}{" "}
              {total === 1 ? "review" : "reviews"}
            </p>
          </>
        )}
      </div>

      <div
        data-testid="review-scroll"
        className="max-h-[42rem] overflow-y-auto overscroll-contain px-6"
      >
        {error && (
          <div className="py-4">
            <ErrorMessage message={error} />
          </div>
        )}
        {!error && reviews === null && (
          <p className="py-4 text-sm text-slate-600">Loading saved reviews…</p>
        )}
        {reviews?.length === 0 && (
          <p className="py-4 text-sm text-slate-600">
            No reviews saved yet. Use Collect reviews to get them from the
            source.
          </p>
        )}
        {total > 0 && visible.length === 0 && filtering && (
          <div className="space-y-2 py-8 text-center">
            <p className="text-sm text-slate-600">
              No reviews match
              {query.trim() ? ` "${query.trim()}"` : ""}
              {stars !== null ? ` with ${stars} stars` : ""}.
            </p>
            <button
              type="button"
              onClick={clearFilters}
              className="text-sm font-medium text-indigo-700 hover:underline"
            >
              Clear filters
            </button>
          </div>
        )}
        {visible.length > 0 && (
          <ul className="divide-y divide-slate-200">
            {visible.map((review) => (
              <li
                key={review.id}
                ref={(node) => {
                  if (node) items.current.set(review.id, node);
                  else items.current.delete(review.id);
                }}
                data-focused={focused === review.id || undefined}
                className={`-mx-3 flex gap-3 rounded-lg px-3 py-4 transition-colors duration-700 ${
                  focused === review.id
                    ? "bg-amber-50 ring-2 ring-amber-300"
                    : ""
                }`}
              >
                <Avatar
                  name={review.reviewer_name}
                  src={review.reviewer_avatar_url}
                />
                <div className="min-w-0 flex-1 space-y-1">
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
                    <span className="font-medium text-slate-800">
                      <Highlight
                        text={review.reviewer_name ?? "Anonymous"}
                        query={query}
                      />
                    </span>
                    <Stars rating={review.rating} />
                    {review.review_date && (
                      <span className="text-slate-500">
                        {review.review_date}
                      </span>
                    )}
                  </div>
                  <p className="whitespace-pre-line text-slate-700">
                    <Highlight text={review.text} query={query} />
                  </p>
                  <ReviewPhotos
                    review={review}
                    onOpen={(photos, index) => setOpen({ photos, index })}
                  />
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {open && (
        <PhotoLightbox
          photos={open.photos}
          index={open.index}
          onClose={() => setOpen(null)}
          onNavigate={(index) => setOpen({ ...open, index })}
        />
      )}
    </section>
  );
}
