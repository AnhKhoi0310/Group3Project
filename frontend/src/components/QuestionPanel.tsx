import {
  useEffect,
  useId,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import { ApiError, type ApiClient } from "../api/client";
import { askQuestion, type QuestionAnswer } from "../api/questions";
import Avatar from "./Avatar";
import Button from "./Button";
import PhotoLightbox, { type Photo } from "./PhotoLightbox";
import { ReviewPhotos } from "./ReviewList";
import Stars from "./Stars";

export const MAX_QUESTION_LENGTH = 1000;
const QUESTION_REQUIRED = "Type a question about this target's reviews.";
const UNEXPECTED =
  "ReviewLens couldn't answer that right now. Please try again.";
const EVIDENCE_PREVIEW_LENGTH = 220;
const EVIDENCE_SHOWN = 3;

export const SUGGESTED_QUESTIONS = [
  "What do customers like most?",
  "What are the most common complaints?",
  "What do low-rated reviews have in common?",
  "How do reviewers describe the service?",
];

interface Props {
  api: ApiClient;
  targetId: string;
  targetName: string;
  platformLabel?: string;
  /**
   * Saved reviews for this target. "loading" while it is being fetched; null
   * when unknown, in which case questions stay available and the backend
   * still refuses to answer without reviews.
   */
  reviewCount?: number | null | "loading";
  /** True while reviews are being collected for this target. */
  collecting?: boolean;
  /** Starts a review collection from the empty state. */
  onCollect?: () => void;
  /** Hides the chat (shown as a close button in the header). */
  onClose?: () => void;
  /** Jumps to a cited review in the review list. */
  onShowReview?: (reviewId: number) => void;
}

interface Entry {
  id: number;
  question: string;
  pending: boolean;
  result?: QuestionAnswer;
  error?: string;
}

type Tone = "answered" | "insufficient" | "declined" | "failed";

const TONES: Record<Tone, { card: string; badge: string; icon: string }> = {
  answered: {
    card: "border-indigo-200 bg-white",
    badge: "border-indigo-300 bg-indigo-50 text-indigo-800",
    icon: "✓",
  },
  insufficient: {
    card: "border-amber-200 bg-amber-50/70",
    badge: "border-amber-300 bg-white text-amber-800",
    icon: "?",
  },
  declined: {
    card: "border-slate-200 bg-slate-50",
    badge: "border-slate-300 bg-white text-slate-700",
    icon: "⦸",
  },
  failed: {
    card: "border-rose-200 bg-rose-50/70",
    badge: "border-rose-300 bg-white text-rose-800",
    icon: "!",
  },
};

function describeResult(result: QuestionAnswer): { label: string; tone: Tone } {
  if (result.status === "answered") {
    return { label: "Answer from the reviews", tone: "answered" };
  }
  if (result.status === "insufficient_evidence") {
    return {
      label:
        result.reviews_used === 0
          ? "No reviews to analyze yet"
          : "Not enough evidence in the reviews",
      tone: "insufficient",
    };
  }
  return { label: "Outside ReviewLens's scope", tone: "declined" };
}

function describeBasis(result: QuestionAnswer): string {
  const reviews = (n: number) => `${n} ${n === 1 ? "review" : "reviews"}`;
  if (result.reviews_total > result.reviews_used) {
    return `Based on the ${result.reviews_used} most recent of ${reviews(result.reviews_total)} for ${result.target_name}.`;
  }
  return `Based on ${reviews(result.reviews_used)} for ${result.target_name}.`;
}

function preview(text: string): string {
  return text.length > EVIDENCE_PREVIEW_LENGTH
    ? `${text.slice(0, EVIDENCE_PREVIEW_LENGTH).trimEnd()}…`
    : text;
}

function Badge({ tone, label }: { tone: Tone; label: string }) {
  return (
    <span
      data-testid="qa-status"
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${TONES[tone].badge}`}
    >
      <span aria-hidden="true">{TONES[tone].icon}</span>
      {label}
    </span>
  );
}

function BotMark() {
  return (
    <span
      aria-hidden="true"
      className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-violet-500 text-xs font-bold text-white shadow"
    >
      RL
    </span>
  );
}

function Evidence({
  result,
  onOpenPhotos,
  onShowReview,
}: {
  result: QuestionAnswer;
  onOpenPhotos: (photos: Photo[], index: number) => void;
  onShowReview?: (reviewId: number) => void;
}) {
  const [showAll, setShowAll] = useState(false);
  const shown = showAll
    ? result.evidence
    : result.evidence.slice(0, EVIDENCE_SHOWN);

  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        Reviews this answer is based on
      </h3>
      <ul className="mt-2 space-y-2">
        {shown.map((review) => (
          <li
            key={review.id}
            className="flex gap-2.5 rounded-md border border-slate-200 bg-white p-2.5 text-sm"
          >
            <Avatar
              name={review.reviewer_name}
              src={review.reviewer_avatar_url}
              size="sm"
            />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-x-2">
                <span className="font-medium">
                  {review.reviewer_name ?? "Anonymous"}
                </span>
                <Stars rating={review.rating} className="text-xs" />
              </div>
              <p className="mt-1 text-slate-700">{preview(review.text)}</p>
              <ReviewPhotos review={review} onOpen={onOpenPhotos} />
              {onShowReview && (
                <button
                  type="button"
                  onClick={() => onShowReview(review.id)}
                  className="mt-1 text-xs font-medium text-indigo-700 hover:underline"
                >
                  Show in reviews
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
      {result.evidence.length > EVIDENCE_SHOWN && (
        <button
          type="button"
          onClick={() => setShowAll((value) => !value)}
          className="mt-2 text-sm font-medium text-indigo-700 hover:underline"
        >
          {showAll
            ? "Show fewer reviews"
            : `Show all ${result.evidence.length} cited reviews`}
        </button>
      )}
    </div>
  );
}

/**
 * A chat about the active target's reviews, built to fill a side column.
 * Messages read top to bottom and scroll on their own; the question box stays
 * at the bottom. The parent renders it with key={targetId}, so switching
 * targets always starts a new, empty conversation.
 */
export default function QuestionPanel({
  api,
  targetId,
  targetName,
  platformLabel = "Google Maps",
  reviewCount = null,
  collecting = false,
  onCollect,
  onClose,
  onShowReview,
}: Props) {
  const inputId = useId();
  const errorId = `${inputId}-error`;
  const hintId = `${inputId}-hint`;
  const nextId = useRef(1);
  const endOfMessages = useRef<HTMLDivElement>(null);
  const [question, setQuestion] = useState("");
  const [fieldError, setFieldError] = useState("");
  const [entries, setEntries] = useState<Entry[]>([]);
  const [copied, setCopied] = useState<number | null>(null);
  const [photos, setPhotos] = useState<{ list: Photo[]; index: number } | null>(
    null,
  );

  const checking = reviewCount === "loading";
  const noReviews = reviewCount === 0;
  const ready = !collecting && !checking && !noReviews;
  const asking = entries.some((entry) => entry.pending);

  useEffect(() => {
    endOfMessages.current?.scrollIntoView?.({
      behavior: "smooth",
      block: "end",
    });
  }, [entries]);

  function update(id: number, change: Partial<Entry>) {
    setEntries((current) =>
      current.map((entry) =>
        entry.id === id ? { ...entry, ...change } : entry,
      ),
    );
  }

  async function run(id: number, text: string) {
    try {
      const result = await askQuestion(api, targetId, text);
      update(id, { pending: false, result, error: undefined });
    } catch (caught) {
      if (caught instanceof ApiError && caught.fieldErrors.question) {
        setEntries((current) => current.filter((entry) => entry.id !== id));
        setFieldError(caught.fieldErrors.question);
        setQuestion(text);
        return;
      }
      update(id, {
        pending: false,
        error: caught instanceof ApiError ? caught.message : UNEXPECTED,
      });
    }
  }

  function ask(text: string) {
    const trimmed = text.trim();
    if (!trimmed) {
      setFieldError(QUESTION_REQUIRED);
      return;
    }
    if (!ready || asking) return;
    const id = nextId.current++;
    setFieldError("");
    setQuestion("");
    setEntries((current) => [
      ...current,
      { id, question: trimmed, pending: true },
    ]);
    void run(id, trimmed);
  }

  function retry(entry: Entry) {
    if (asking) return;
    update(entry.id, { pending: true, error: undefined });
    void run(entry.id, entry.question);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    ask(question);
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (
      event.key === "Enter" &&
      !event.shiftKey &&
      !event.nativeEvent.isComposing
    ) {
      event.preventDefault();
      ask(question);
    }
  }

  function copy(entry: Entry) {
    if (!entry.result) return;
    navigator.clipboard
      ?.writeText(entry.result.answer)
      .then(() => setCopied(entry.id))
      .catch(() => {});
  }

  const openPhotos = (list: Photo[], index: number) =>
    setPhotos({ list, index });

  const countLabel =
    typeof reviewCount === "number"
      ? `${reviewCount} ${platformLabel} ${reviewCount === 1 ? "review" : "reviews"}`
      : `${platformLabel} reviews`;

  return (
    <section
      aria-labelledby={`${inputId}-heading`}
      className="flex h-full flex-col bg-white"
    >
      <header className="space-y-3 border-b border-slate-200 bg-gradient-to-b from-indigo-50 to-white p-4">
        <div className="flex items-start gap-3">
          <BotMark />
          <div className="min-w-0 flex-1">
            <h2
              id={`${inputId}-heading`}
              className="truncate text-base font-semibold"
            >
              Ask about {targetName}
            </h2>
            <p className="text-xs text-slate-600">
              Answers only from the saved reviews for {targetName}.
            </p>
          </div>
          {entries.length > 0 && (
            <button
              type="button"
              disabled={asking}
              onClick={() => setEntries([])}
              className="rounded-md px-2 py-1 text-xs text-slate-600 hover:bg-slate-100 hover:text-slate-900 disabled:opacity-50"
            >
              Clear questions
            </button>
          )}
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              aria-label="Hide chat"
              className="rounded-md px-2 py-1 text-lg leading-none text-slate-500 hover:bg-slate-100 hover:text-slate-900"
            >
              ×
            </button>
          )}
        </div>
        {ready && (
          <ul
            aria-label="What ReviewLens can answer"
            className="flex flex-wrap gap-1.5 text-xs"
          >
            <li className="rounded-full bg-emerald-50 px-2 py-0.5 font-medium text-emerald-800 ring-1 ring-emerald-200">
              ✓ Answers from {countLabel} of {targetName}
            </li>
            {[
              "Other businesses",
              "Other review sites",
              "General knowledge",
            ].map((item) => (
              <li
                key={item}
                className="rounded-full bg-white px-2 py-0.5 text-slate-600 ring-1 ring-slate-200"
              >
                <span aria-hidden="true">✕ </span>
                <span className="sr-only">Can't answer: </span>
                {item}
              </li>
            ))}
          </ul>
        )}
      </header>

      <div
        data-testid="chat-messages"
        className="flex-1 space-y-4 overflow-y-auto overscroll-contain bg-slate-50/60 p-4"
      >
        {noReviews && !collecting && (
          <div
            role="status"
            className="space-y-3 rounded-lg border border-dashed border-slate-300 bg-white p-4 text-center"
          >
            <span aria-hidden="true" className="text-3xl">
              ✦
            </span>
            <p className="font-medium">No reviews to analyze yet</p>
            <p className="text-sm text-slate-600">
              ReviewLens only answers from collected reviews, so questions open
              once reviews for {targetName} are saved.
            </p>
            {onCollect && (
              <Button variant="secondary" onClick={onCollect}>
                Collect reviews now
              </Button>
            )}
          </div>
        )}

        {collecting && (
          <p
            role="status"
            className="flex items-center gap-2 rounded-lg bg-indigo-50 p-3 text-sm text-indigo-800"
          >
            <span
              aria-hidden="true"
              className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-indigo-300 border-t-indigo-700"
            />
            Collecting reviews for {targetName}. Questions open as soon as it
            finishes.
          </p>
        )}

        {checking && !collecting && (
          <p className="text-sm text-slate-600">Checking the review dataset…</p>
        )}

        {ready && entries.length === 0 && (
          <div className="flex gap-2">
            <BotMark />
            <div className="rounded-2xl rounded-tl-sm border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm">
              I've read the {countLabel} of {targetName}. Ask me what customers
              praise, complain about, or say about anything specific. I'll show
              you the reviews behind each answer.
            </div>
          </div>
        )}

        {entries.length > 0 && (
          <ol
            aria-label={`Your questions about ${targetName}`}
            className="space-y-4"
          >
            {entries.map((entry) => (
              <li key={entry.id} className="space-y-2">
                <p className="ml-auto w-fit max-w-[85%] rounded-2xl rounded-br-sm bg-indigo-600 px-3 py-2 text-sm text-white shadow-sm">
                  <span className="sr-only">You asked: </span>
                  {entry.question}
                </p>

                <div className="flex gap-2">
                  <BotMark />
                  <div className="min-w-0 flex-1">
                    {entry.pending && (
                      <div
                        role="status"
                        className="space-y-2 rounded-2xl rounded-tl-sm border border-slate-200 bg-white p-3"
                      >
                        <p className="text-sm text-slate-600">
                          Reading the reviews for {targetName}…
                        </p>
                        <div aria-hidden="true" className="flex gap-1">
                          {[0, 150, 300].map((delay) => (
                            <span
                              key={delay}
                              style={{ animationDelay: `${delay}ms` }}
                              className="h-2 w-2 animate-bounce rounded-full bg-indigo-400"
                            />
                          ))}
                        </div>
                      </div>
                    )}

                    {entry.error && (
                      <div
                        role="alert"
                        className={`space-y-2 rounded-2xl rounded-tl-sm border p-3 ${TONES.failed.card}`}
                      >
                        <Badge
                          tone="failed"
                          label="ReviewLens couldn't answer"
                        />
                        <p className="text-sm text-slate-800">{entry.error}</p>
                        <Button
                          variant="secondary"
                          disabled={asking}
                          onClick={() => retry(entry)}
                        >
                          Try again
                        </Button>
                      </div>
                    )}

                    {entry.result &&
                      (() => {
                        const { label, tone } = describeResult(entry.result);
                        return (
                          <div
                            data-testid="qa-result"
                            aria-live="polite"
                            className={`space-y-3 rounded-2xl rounded-tl-sm border p-3 shadow-sm ${TONES[tone].card}`}
                          >
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <Badge tone={tone} label={label} />
                              {entry.result.status === "answered" && (
                                <button
                                  type="button"
                                  onClick={() => copy(entry)}
                                  className="text-xs font-medium text-slate-600 hover:text-slate-900"
                                >
                                  {copied === entry.id
                                    ? "Copied"
                                    : "Copy answer"}
                                </button>
                              )}
                            </div>
                            <p className="whitespace-pre-line text-sm text-slate-800">
                              {entry.result.answer}
                            </p>
                            {entry.result.reviews_used > 0 && (
                              <p className="text-xs text-slate-500">
                                {describeBasis(entry.result)}
                              </p>
                            )}
                            {entry.result.evidence.length > 0 && (
                              <Evidence
                                result={entry.result}
                                onOpenPhotos={openPhotos}
                                onShowReview={onShowReview}
                              />
                            )}
                          </div>
                        );
                      })()}
                  </div>
                </div>
              </li>
            ))}
          </ol>
        )}
        <div ref={endOfMessages} />
      </div>

      <form
        onSubmit={submit}
        noValidate
        className="border-t border-slate-200 bg-white p-3"
      >
        <fieldset disabled={!ready} className="space-y-2 disabled:opacity-60">
          <div
            aria-label="Suggested questions"
            role="group"
            className="-mx-1 flex snap-x gap-2 overflow-x-auto px-1 pb-1 [scrollbar-width:thin]"
          >
            {SUGGESTED_QUESTIONS.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                disabled={asking}
                onClick={() => ask(suggestion)}
                className="shrink-0 snap-start whitespace-nowrap rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs text-indigo-800 transition hover:-translate-y-0.5 hover:bg-indigo-100 disabled:opacity-50 disabled:hover:translate-y-0"
              >
                {suggestion}
              </button>
            ))}
          </div>
          <div>
            <label htmlFor={inputId} className="sr-only">
              Your question
            </label>
            <div
              className={`flex items-end gap-2 rounded-xl border bg-white p-2 focus-within:ring-2 focus-within:ring-indigo-200 ${
                fieldError ? "border-red-500" : "border-slate-300"
              }`}
            >
              <textarea
                id={inputId}
                rows={2}
                maxLength={MAX_QUESTION_LENGTH}
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                onKeyDown={onKeyDown}
                placeholder={`Ask about ${targetName}…`}
                aria-invalid={fieldError ? true : undefined}
                aria-describedby={fieldError ? `${errorId} ${hintId}` : hintId}
                className="max-h-40 min-h-[2.5rem] flex-1 resize-y border-0 bg-transparent px-1 text-sm focus:outline-none"
              />
              <Button type="submit" disabled={asking} className="shrink-0">
                {asking ? "Reading the reviews…" : "Ask ReviewLens"}
              </Button>
            </div>
            {fieldError && (
              <p
                id={errorId}
                role="alert"
                className="mt-1 text-sm text-red-700"
              >
                {fieldError}
              </p>
            )}
            <p
              id={hintId}
              className="mt-1 flex justify-between text-[11px] text-slate-500"
            >
              <span>Enter to ask · Shift+Enter for a new line</span>
              <span>
                {question.length} / {MAX_QUESTION_LENGTH}
              </span>
            </p>
          </div>
        </fieldset>
      </form>

      {photos && (
        <PhotoLightbox
          photos={photos.list}
          index={photos.index}
          onClose={() => setPhotos(null)}
          onNavigate={(index) => setPhotos({ ...photos, index })}
        />
      )}
    </section>
  );
}
