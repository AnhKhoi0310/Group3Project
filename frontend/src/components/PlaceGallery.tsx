import { useEffect, useState } from "react";
import type { ApiClient } from "../api/client";
import { listReviews, type Review } from "../api/reviews";
import { colorFor, initials } from "./Avatar";
import PhotoLightbox, { type Photo } from "./PhotoLightbox";

const MAX_PHOTOS = 24;
const TILES = 5;

interface Props {
  api: ApiClient;
  targetId: string;
  targetName: string;
  /** Change this value to reload, for example after a collection finishes. */
  refreshKey: number;
}

export function photosFromReviews(reviews: Review[]): Photo[] {
  const photos: Photo[] = [];
  for (const review of reviews) {
    const by = review.reviewer_name ?? "A reviewer";
    for (const url of review.image_urls ?? []) {
      if (photos.length === MAX_PHOTOS) return photos;
      photos.push({ url, caption: `${by}, ${review.rating} out of 5` });
    }
  }
  return photos;
}

/**
 * Photos that reviewers posted with their reviews. Google Maps doesn't give us
 * a photo of the place itself, so these stand in for it. Without photos, a
 * lettered tile keeps the target recognizable.
 */
export default function PlaceGallery({
  api,
  targetId,
  targetName,
  refreshKey,
}: Props) {
  const [photos, setPhotos] = useState<Photo[] | null>(null);
  const [open, setOpen] = useState<number | null>(null);

  useEffect(() => {
    let active = true;
    setPhotos(null);
    setOpen(null);
    listReviews(api, targetId)
      .then((items) => {
        if (active)
          setPhotos(photosFromReviews(Array.isArray(items) ? items : []));
      })
      .catch(() => {
        // Photos are decoration; the review list reports load errors.
        if (active) setPhotos([]);
      });
    return () => {
      active = false;
    };
  }, [api, targetId, refreshKey]);

  if (photos === null) {
    return (
      <div
        aria-hidden="true"
        className="h-40 animate-pulse rounded-lg border border-slate-200 bg-slate-100"
      />
    );
  }

  if (photos.length === 0) {
    return (
      <section
        aria-label={`Photos of ${targetName}`}
        className="flex items-center gap-5 rounded-lg border border-slate-200 bg-white p-6"
      >
        <span
          aria-hidden="true"
          className={`${colorFor(targetName)} flex h-24 w-24 shrink-0 items-center justify-center rounded-2xl text-3xl font-bold shadow-inner`}
        >
          {initials(targetName)}
        </span>
        <div>
          <h2 className="text-lg font-semibold">No customer photos yet</h2>
          <p className="mt-1 text-sm text-slate-600">
            Photos that reviewers post on Google Maps appear here after you
            collect reviews.
          </p>
        </div>
      </section>
    );
  }

  const tiles = photos.slice(0, TILES);
  const hidden = photos.length - tiles.length;

  return (
    <section
      aria-labelledby="place-gallery-heading"
      className="space-y-3 rounded-lg border border-slate-200 bg-white p-6"
    >
      <div className="flex items-baseline justify-between gap-2">
        <h2 id="place-gallery-heading" className="text-lg font-semibold">
          Photos from customers
        </h2>
        <span className="text-sm text-slate-600">
          {photos.length} {photos.length === 1 ? "photo" : "photos"} from
          reviews of {targetName}
        </span>
      </div>
      <ul className="grid h-56 grid-cols-4 grid-rows-2 gap-2">
        {tiles.map((photo, index) => {
          const isLastTile = index === tiles.length - 1 && hidden > 0;
          return (
            <li
              key={photo.url}
              className={index === 0 ? "col-span-2 row-span-2" : ""}
            >
              <button
                type="button"
                onClick={() => setOpen(index)}
                aria-label={
                  isLastTile
                    ? `Open photo ${index + 1} of ${photos.length}, plus ${hidden} more`
                    : `Open photo ${index + 1} of ${photos.length}: ${photo.caption}`
                }
                className="group relative h-full w-full overflow-hidden rounded-md bg-slate-100 focus-visible:outline-2 focus-visible:outline-indigo-600"
              >
                <img
                  src={photo.url}
                  alt=""
                  loading="lazy"
                  referrerPolicy="no-referrer"
                  className="h-full w-full object-cover transition duration-300 group-hover:scale-105"
                />
                {isLastTile && (
                  <span className="absolute inset-0 flex items-center justify-center bg-slate-900/60 text-lg font-semibold text-white">
                    +{hidden}
                  </span>
                )}
              </button>
            </li>
          );
        })}
      </ul>
      {open !== null && (
        <PhotoLightbox
          photos={photos}
          index={open}
          onClose={() => setOpen(null)}
          onNavigate={setOpen}
        />
      )}
    </section>
  );
}
