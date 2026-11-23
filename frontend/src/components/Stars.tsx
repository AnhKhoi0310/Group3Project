/** Star rating with a text equivalent for screen readers. */
export default function Stars({
  rating,
  className = "",
}: {
  rating: number;
  className?: string;
}) {
  const filled = Math.max(0, Math.min(5, Math.round(rating)));
  return (
    <span
      role="img"
      aria-label={`${rating} out of 5 stars`}
      className={`text-amber-500 ${className}`}
    >
      {"★".repeat(filled)}
      <span className="text-slate-300">{"★".repeat(5 - filled)}</span>
    </span>
  );
}
