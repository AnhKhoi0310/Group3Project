import { useState } from "react";

const PALETTE = [
  "bg-indigo-100 text-indigo-700",
  "bg-emerald-100 text-emerald-700",
  "bg-amber-100 text-amber-800",
  "bg-rose-100 text-rose-700",
  "bg-sky-100 text-sky-700",
  "bg-violet-100 text-violet-700",
];

const SIZES = {
  sm: "h-7 w-7 text-xs",
  md: "h-9 w-9 text-sm",
  xl: "h-24 w-24 text-3xl",
} as const;

export function initials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return "?";
  const first = words[0][0];
  const last = words.length > 1 ? words[words.length - 1][0] : "";
  return `${first}${last}`.toUpperCase();
}

/** The same name always gets the same color. */
export function colorFor(name: string): string {
  let hash = 0;
  for (const char of name) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return PALETTE[hash % PALETTE.length];
}

interface Props {
  name: string | null;
  src?: string | null;
  size?: keyof typeof SIZES;
}

/**
 * A profile picture, or colored initials when there is no picture or it
 * fails to load. Decorative: the name is always shown as text next to it.
 */
export default function Avatar({ name, src, size = "md" }: Props) {
  const [failed, setFailed] = useState(false);
  const label = name?.trim() || "Anonymous";

  if (src && !failed) {
    return (
      <img
        src={src}
        alt=""
        loading="lazy"
        referrerPolicy="no-referrer"
        onError={() => setFailed(true)}
        data-testid="avatar-image"
        className={`${SIZES[size]} shrink-0 rounded-full bg-slate-100 object-cover`}
      />
    );
  }

  return (
    <span
      aria-hidden="true"
      data-testid="avatar-initials"
      className={`${SIZES[size]} ${colorFor(label)} inline-flex shrink-0 items-center justify-center rounded-full font-semibold`}
    >
      {initials(label)}
    </span>
  );
}
