import { useEffect, useRef } from "react";

export interface Photo {
  url: string;
  caption: string;
}

interface Props {
  photos: Photo[];
  index: number;
  onClose: () => void;
  onNavigate: (index: number) => void;
}

/**
 * Full-size view of customer photos. Escape closes it; the arrow keys and the
 * Previous and Next buttons move between photos.
 */
export default function PhotoLightbox({
  photos,
  index,
  onClose,
  onNavigate,
}: Props) {
  const closeButton = useRef<HTMLButtonElement>(null);
  const count = photos.length;

  useEffect(() => {
    closeButton.current?.focus();
  }, []);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
      else if (event.key === "ArrowRight") onNavigate((index + 1) % count);
      else if (event.key === "ArrowLeft") {
        onNavigate((index - 1 + count) % count);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [index, count, onClose, onNavigate]);

  const photo = photos[index];
  if (!photo) return null;

  const navButton =
    "rounded-full bg-white/90 px-3 py-2 text-sm font-medium text-slate-900 shadow hover:bg-white focus-visible:outline-2 focus-visible:outline-white";

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`Photo ${index + 1} of ${count}`}
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/85 p-4"
      onClick={onClose}
    >
      <figure
        className="flex max-h-full w-full max-w-3xl flex-col items-center"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="mb-3 flex w-full justify-end">
          <button
            ref={closeButton}
            type="button"
            onClick={onClose}
            className={navButton}
          >
            Close
          </button>
        </div>
        <img
          src={photo.url}
          alt={photo.caption}
          referrerPolicy="no-referrer"
          className="max-h-[70vh] w-auto rounded-lg object-contain shadow-2xl"
        />
        <figcaption className="mt-3 text-center text-sm text-slate-100">
          {photo.caption} · {index + 1} of {count}
        </figcaption>
        {count > 1 && (
          <div className="mt-4 flex gap-3">
            <button
              type="button"
              className={navButton}
              onClick={() => onNavigate((index - 1 + count) % count)}
            >
              Previous photo
            </button>
            <button
              type="button"
              className={navButton}
              onClick={() => onNavigate((index + 1) % count)}
            >
              Next photo
            </button>
          </div>
        )}
      </figure>
    </div>
  );
}
