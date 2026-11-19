import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { ApiError } from "../api/client";
import {
  getLatestIngestion,
  startIngestion,
  type IngestionAttempt,
} from "../api/ingestions";
import { getTarget, type AnalysisTarget } from "../api/targets";
import { useAuth } from "../auth/AuthContext";
import Button from "../components/Button";
import ErrorMessage from "../components/ErrorMessage";
import LoadingIndicator from "../components/LoadingIndicator";
import ReviewList from "../components/ReviewList";
import ReviewSummaryCard from "../components/ReviewSummaryCard";

const PLATFORM_LABELS: Record<string, string> = { google_maps: "Google Maps" };
const UNEXPECTED = "Something went wrong on our side. Please try again.";

function describeFailure(category: string | null | undefined): string {
  const messages: Record<string, string> = {
    invalid_source:
      "The saved review link could not be used. Check the link and try again.",
    provider_timeout:
      "The review source took too long to respond. Try again in a few minutes.",
    provider_quota:
      "The review collection limit has been reached. Try again later.",
    provider_unavailable:
      "The review source is unavailable. Try again in a few minutes.",
    persistence_error:
      "Reviews were collected but could not be saved. Try again.",
  };
  return (
    messages[category ?? ""] ??
    "The previous review collection attempt failed. Try again."
  );
}

const SKIP_REASON_LABELS: Record<string, string> = {
  missing_text: "missing review text",
  invalid_rating: "invalid rating",
  malformed_record: "malformed source record",
  duplicate_record: "duplicate review",
};

function formatSkippedReasons(
  reasons: Record<string, number> | undefined,
): string {
  if (!reasons) return "";
  const parts = Object.entries(reasons)
    .filter(([, count]) => count > 0)
    .map(
      ([reason, count]) =>
        `${count} (${SKIP_REASON_LABELS[reason] ?? reason.replace(/_/g, " ")})`,
    );
  return parts.length > 0 ? `: ${parts.join(", ")}` : "";
}

function describeAttempt(attempt: IngestionAttempt): string {
  const found = `Found ${attempt.reviews_found} ${
    attempt.reviews_found === 1 ? "review" : "reviews"
  }.`;
  if (attempt.reviews_skipped === 0) return found;
  const breakdown = formatSkippedReasons(attempt.skipped_reasons);
  return `${found} ${attempt.reviews_skipped} ${
    attempt.reviews_skipped === 1 ? "was" : "were"
  } skipped and excluded from the active dataset${breakdown}.`;
}

type DisplayIngestionStatus =
  "Not started" | "Processing" | "Succeeded" | "Partial success" | "Failed";

function getDisplayStatus(
  busy: boolean,
  attempt: IngestionAttempt | null,
): DisplayIngestionStatus {
  if (busy || attempt?.status === "processing") {
    return "Processing";
  }
  if (!attempt) {
    return "Not started";
  }
  if (attempt.status === "failed") {
    return "Failed";
  }
  if (attempt.reviews_skipped > 0 || attempt.reviews_found === 0) {
    return "Partial success";
  }
  return "Succeeded";
}

function getStatusBadgeClasses(status: DisplayIngestionStatus): string {
  switch (status) {
    case "Succeeded":
      return "border-emerald-300 bg-emerald-50 text-emerald-800";
    case "Partial success":
      return "border-amber-300 bg-amber-50 text-amber-800";
    case "Failed":
      return "border-rose-300 bg-rose-50 text-rose-800";
    case "Processing":
      return "border-indigo-300 bg-indigo-50 text-indigo-800";
    default:
      return "border-slate-300 bg-slate-100 text-slate-700";
  }
}

function describeDatasetReadiness(
  status: DisplayIngestionStatus,
  attempt: IngestionAttempt | null,
): string {
  switch (status) {
    case "Processing":
      return "Ingestion is currently running. Analysis will be ready once collection finishes.";
    case "Succeeded":
      return attempt && attempt.reviews_found === 0
        ? "Ingestion completed, but no usable reviews were added to the dataset."
        : "Dataset is ready for analysis.";
    case "Partial success":
      return attempt && attempt.reviews_found > 0
        ? "Dataset is ready for analysis, though some source records were skipped."
        : "Ingestion finished, but no usable reviews were added to the dataset.";
    case "Failed":
      return "The latest ingestion attempt failed. Any previously saved reviews remain available.";
    default:
      return "No ingestion has been run for this target yet. Collect reviews to build an analysis dataset.";
  }
}

export default function TargetWorkspacePage() {
  const { api } = useAuth();
  const { targetId } = useParams();
  const location = useLocation();
  const justCreated =
    (location.state as { created?: boolean } | null)?.created === true;
  const [target, setTarget] = useState<AnalysisTarget | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [attempt, setAttempt] = useState<IngestionAttempt | null>(null);
  const [ingestError, setIngestError] = useState("");
  const [reviewsVersion, setReviewsVersion] = useState(0);

  useEffect(() => {
    if (!targetId) return;
    const id = targetId;
    let active = true;
    setTarget(null);
    setError("");
    setAttempt(null);
    setIngestError("");

    async function load() {
      try {
        const item = await getTarget(api, id);
        if (!active) return;
        setTarget(item);

        const latest = await getLatestIngestion(api, id);
        if (!active) return;
        setAttempt(latest);
        if (latest?.status === "failed") {
          setIngestError(describeFailure(latest.failure_category));
        }
      } catch (caught) {
        if (!active) return;
        setError(caught instanceof ApiError ? caught.message : UNEXPECTED);
      }
    }

    void load();
    return () => {
      active = false;
    };
  }, [api, targetId]);

  async function collect() {
    if (!target) return;
    setBusy(true);
    setIngestError("");
    try {
      const latest = await startIngestion(api, target.id);
      // Keep the page tolerant of older mocked API responses during migration.
      setAttempt({ ...latest, status: latest.status ?? "succeeded" });
    } catch (caught) {
      setIngestError(caught instanceof ApiError ? caught.message : UNEXPECTED);
      // The POST reports a friendly error; fetch the persisted attempt so the
      // workspace still displays the backend's authoritative failed state.
      try {
        setAttempt(await getLatestIngestion(api, String(target.id)));
      } catch {
        // Keep the original user-facing ingestion error.
      }
    } finally {
      setBusy(false);
      setReviewsVersion((version) => version + 1);
    }
  }

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-semibold">Analysis workspace</h1>
        <ErrorMessage message={error} />
        <Link to="/targets" className="text-sm font-medium text-indigo-700">
          Back to your targets
        </Link>
      </div>
    );
  }

  if (!target) return <LoadingIndicator />;

  const displayStatus = getDisplayStatus(busy, attempt);
  const isProcessing = busy || attempt?.status === "processing";

  return (
    <div className="space-y-6">
      <div>
        <Link to="/targets" className="text-sm font-medium text-indigo-700">
          Back to your targets
        </Link>
        <h1 className="mt-2 text-2xl font-semibold">{target.name}</h1>
        <p className="mt-1 text-sm text-slate-600">
          {PLATFORM_LABELS[target.platform] ?? target.platform}
        </p>
        <p className="mt-1 text-sm text-slate-600">
          <a
            href={target.source_url}
            target="_blank"
            rel="noreferrer"
            className="break-all text-indigo-700"
          >
            {target.source_url}
          </a>
        </p>
      </div>
      {justCreated && (
        <p
          role="status"
          className="rounded-lg border border-slate-200 bg-white p-4 text-slate-700"
        >
          Target created. It is saved to your account.
        </p>
      )}
      <section
        aria-labelledby="ingestion-status-heading"
        className="space-y-4 rounded-lg border border-slate-200 bg-white p-6"
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 id="ingestion-status-heading" className="text-lg font-semibold">
            Ingestion status for {target.name}
          </h2>
          <span
            data-testid="ingestion-status-badge"
            className={`rounded-md border px-2.5 py-0.5 text-sm font-medium ${getStatusBadgeClasses(displayStatus)}`}
          >
            {displayStatus}
          </span>
        </div>

        <p className="text-sm text-slate-700">
          {describeDatasetReadiness(displayStatus, attempt)}
        </p>

        <Button onClick={collect} disabled={isProcessing}>
          {isProcessing ? "Collecting reviews…" : "Collect reviews"}
        </Button>

        {ingestError && <ErrorMessage message={ingestError} />}
        {attempt?.status === "succeeded" && (
          <p role="status" className="text-sm text-slate-700">
            {describeAttempt(attempt)}
          </p>
        )}
      </section>
      <ReviewSummaryCard
        api={api}
        targetId={String(target.id)}
        targetName={target.name}
        refreshKey={reviewsVersion}
      />
      <ReviewList
        api={api}
        targetId={String(target.id)}
        refreshKey={reviewsVersion}
      />
    </div>
  );
}
