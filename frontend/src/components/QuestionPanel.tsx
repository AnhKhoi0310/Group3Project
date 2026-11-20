import { useId, useState, type FormEvent } from "react";
import { ApiError, type ApiClient } from "../api/client";
import { askQuestion, type QuestionAnswer } from "../api/questions";
import Button from "./Button";
import ErrorMessage from "./ErrorMessage";

export const MAX_QUESTION_LENGTH = 1000;
const QUESTION_REQUIRED = "Type a question about this target's reviews.";
const UNEXPECTED =
  "ReviewLens couldn't answer that right now. Please try again.";
const EVIDENCE_PREVIEW_LENGTH = 280;

interface Props {
  api: ApiClient;
  targetId: string;
  targetName: string;
}

function describeResult(result: QuestionAnswer): {
  label: string;
  classes: string;
} {
  if (result.status === "answered") {
    return {
      label: "Answer from the reviews",
      classes: "border-indigo-300 bg-indigo-50 text-indigo-800",
    };
  }
  if (result.status === "insufficient_evidence") {
    return {
      label:
        result.reviews_used === 0
          ? "No reviews to analyze yet"
          : "Not enough evidence in the reviews",
      classes: "border-amber-300 bg-amber-50 text-amber-800",
    };
  }
  return {
    label: "Outside ReviewLens's scope",
    classes: "border-slate-300 bg-slate-100 text-slate-700",
  };
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

/**
 * Ask one question at a time about the active target. The parent renders it
 * with key={targetId}, so switching targets starts with an empty panel.
 */
export default function QuestionPanel({ api, targetId, targetName }: Props) {
  const inputId = useId();
  const errorId = `${inputId}-error`;
  const [question, setQuestion] = useState("");
  const [fieldError, setFieldError] = useState("");
  const [error, setError] = useState("");
  const [asking, setAsking] = useState(false);
  const [result, setResult] = useState<QuestionAnswer | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed) {
      setFieldError(QUESTION_REQUIRED);
      return;
    }
    setAsking(true);
    setFieldError("");
    setError("");
    setResult(null);
    try {
      setResult(await askQuestion(api, targetId, trimmed));
    } catch (caught) {
      if (caught instanceof ApiError && caught.fieldErrors.question) {
        setFieldError(caught.fieldErrors.question);
      } else {
        setError(caught instanceof ApiError ? caught.message : UNEXPECTED);
      }
    } finally {
      setAsking(false);
    }
  }

  const described = result ? describeResult(result) : null;

  return (
    <section
      aria-labelledby={`${inputId}-heading`}
      className="space-y-4 rounded-lg border border-slate-200 bg-white p-6"
    >
      <div>
        <h2 id={`${inputId}-heading`} className="text-lg font-semibold">
          Ask about {targetName}
        </h2>
        <p className="mt-1 text-sm text-slate-600">
          ReviewLens answers only from the saved reviews for {targetName}. It
          says so when the reviews don't cover your question.
        </p>
      </div>

      <form onSubmit={submit} noValidate className="space-y-3">
        <div>
          <label htmlFor={inputId} className="block text-sm font-medium">
            Your question
          </label>
          <textarea
            id={inputId}
            rows={3}
            maxLength={MAX_QUESTION_LENGTH}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="For example: What do customers complain about most?"
            aria-invalid={fieldError ? true : undefined}
            aria-describedby={fieldError ? errorId : undefined}
            className={`mt-1 w-full rounded-md border bg-white px-3 py-2 ${
              fieldError ? "border-red-500" : "border-slate-300"
            }`}
          />
          {fieldError && (
            <p id={errorId} role="alert" className="mt-1 text-sm text-red-700">
              {fieldError}
            </p>
          )}
        </div>
        <Button type="submit" disabled={asking}>
          {asking ? "Reading the reviews…" : "Ask ReviewLens"}
        </Button>
      </form>

      {asking && (
        <p role="status" className="text-sm text-slate-600">
          Reading the reviews for {targetName}…
        </p>
      )}
      {error && <ErrorMessage message={error} />}

      {result && described && (
        <div
          data-testid="qa-result"
          aria-live="polite"
          className="space-y-3 border-t border-slate-200 pt-4"
        >
          <span
            data-testid="qa-status"
            className={`inline-block rounded-md border px-2.5 py-0.5 text-sm font-medium ${described.classes}`}
          >
            {described.label}
          </span>
          <p className="whitespace-pre-line text-slate-800">{result.answer}</p>
          {result.reviews_used > 0 && (
            <p className="text-sm text-slate-600">{describeBasis(result)}</p>
          )}
          {result.evidence.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold">
                Reviews this answer is based on
              </h3>
              <ul className="mt-2 space-y-2">
                {result.evidence.map((review) => (
                  <li
                    key={review.id}
                    className="rounded-md border border-slate-200 p-3 text-sm"
                  >
                    <span className="font-medium">{review.rating} / 5</span>
                    <span className="text-slate-500">
                      {" · "}
                      {review.reviewer_name ?? "Anonymous"}
                    </span>
                    <p className="mt-1 text-slate-700">
                      {preview(review.text)}
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
