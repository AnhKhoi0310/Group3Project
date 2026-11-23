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
import ChatDock, { clampWidth, DEFAULT_WIDTH } from "../components/ChatDock";
import ErrorMessage from "../components/ErrorMessage";
import LoadingIndicator from "../components/LoadingIndicator";
import PlaceGallery from "../components/PlaceGallery";
import QuestionPanel from "../components/QuestionPanel";
import ReviewList, { focusReview } from "../components/ReviewList";
import ReviewSummaryCard from "../components/ReviewSummaryCard";
import TargetSwitcher from "../components/TargetSwitcher";

const PLATFORM_LABELS: Record<string, string> = {
  google_maps: "Google Maps",
};

const UNEXPECTED = "Something went wrong on our side. Please try again.";
const CHAT_PREFS_KEY = "reviewlens.chat";

function isDesktop(): boolean {
  return (
    typeof window.matchMedia !== "function" ||
    window.matchMedia("(min-width: 1024px)").matches
  );
}

/** Chat open state and width, remembered per browser when storage works. */
function readChatPrefs(): { open: boolean; width: number } {
  const desktop = isDesktop();
  try {
    const saved = JSON.parse(localStorage.getItem(CHAT_PREFS_KEY) ?? "null");
    if (saved && typeof saved.width === "number") {
      return {
        open: desktop && saved.open !== false,
        width: clampWidth(saved.width),
      };
    }
  } catch {
    // Storage can be blocked or hold bad data; fall back to the defaults.
  }
  return { open: desktop, width: DEFAULT_WIDTH };
}

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
      return "Dataset is ready for analysis.";

    case "Partial success":
      return attempt && attempt.reviews_found > 0
        ? "Dataset is ready for analysis, though some source records were skipped."
        : "No successfully ingested reviews are available for this target. Complete a successful review ingestion before asking ReviewLens questions.";

    case "Failed":
      return "The latest ingestion attempt failed. Any previously saved reviews remain available. If no successful ingestion exists, complete a successful review ingestion before asking ReviewLens questions.";

    default:
      return "No reviews have been ingested for this target. Complete a successful review ingestion before asking ReviewLens questions.";
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
  const [chat, setChat] = useState(readChatPrefs);
  const [reviewCount, setReviewCount] = useState<number | null | "loading">(
    "loading",
  );

  useEffect(() => {
    if (!targetId) return;

    const id = targetId;
    let active = true;

    // Clear the previous target's workspace state before loading the next.
    setTarget(null);
    setError("");
    setAttempt(null);
    setIngestError("");
    setBusy(false);
    setReviewCount("loading");

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

  useEffect(() => {
    try {
      localStorage.setItem(CHAT_PREFS_KEY, JSON.stringify(chat));
    } catch {
      // Remembering the layout is a convenience only.
    }
  }, [chat]);

  function showReview(reviewId: number) {
    focusReview(reviewId);
    // On small screens the chat covers the reviews, so step out of the way.
    if (!isDesktop()) setChat((current) => ({ ...current, open: false }));
  }

  async function collect() {
    if (!target) return;

    setBusy(true);
    setIngestError("");

    try {
      const latest = await startIngestion(api, target.id);

      // Keep the page tolerant of older mocked API responses during migration.
      setAttempt({
        ...latest,
        status: latest.status ?? "succeeded",
      });
    } catch (caught) {
      setIngestError(caught instanceof ApiError ? caught.message : UNEXPECTED);

      // Fetch the persisted attempt so the workspace displays the backend's
      // authoritative failed state.
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
  const platformLabel = PLATFORM_LABELS[target.platform] ?? target.platform;
  const closeChat = () => setChat((current) => ({ ...current, open: false }));

  return (
    <div className="lg:flex lg:items-start lg:gap-6">
      <div className="min-w-0 flex-1 space-y-6">
        <div className="grid gap-6 xl:grid-cols-2">
          <div className="space-y-4 rounded-lg border border-slate-200 bg-white p-6">
            <div>
              <Link
                to="/targets"
                className="text-sm font-medium text-indigo-700"
              >
                Back to your targets
              </Link>

              <h1 className="mt-2 text-2xl font-semibold">{target.name}</h1>

              <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
                <span className="rounded-full bg-slate-100 px-2.5 py-0.5 font-medium text-slate-700">
                  {platformLabel}
                </span>
              </div>

              <p className="mt-2 text-sm text-slate-600">
                <a
                  href={target.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="line-clamp-2 break-all text-indigo-700"
                >
                  {target.source_url}
                </a>
              </p>
            </div>

            <TargetSwitcher
              api={api}
              activeTargetId={target.id}
              activeTargetName={target.name}
            />
          </div>

          <PlaceGallery
            api={api}
            targetId={String(target.id)}
            targetName={target.name}
            refreshKey={reviewsVersion}
          />
        </div>

        {justCreated && (
          <p
            role="status"
            className="rounded-lg border border-slate-200 bg-white p-4 text-slate-700"
          >
            Target created. It is saved to your account.
          </p>
        )}

        <div className="grid items-start gap-6 xl:grid-cols-2">
          <section
            aria-labelledby="ingestion-status-heading"
            className="space-y-4 rounded-lg border border-slate-200 bg-white p-6"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2
                id="ingestion-status-heading"
                className="text-lg font-semibold"
              >
                Ingestion status for {target.name}
              </h2>

              <span
                data-testid="ingestion-status-badge"
                className={`rounded-md border px-2.5 py-0.5 text-sm font-medium ${getStatusBadgeClasses(
                  displayStatus,
                )}`}
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
            onReviewCount={setReviewCount}
          />
        </div>

        <ReviewList
          api={api}
          targetId={String(target.id)}
          refreshKey={reviewsVersion}
        />
      </div>

      <ChatDock
        open={chat.open}
        width={chat.width}
        label={`ReviewLens chat about ${target.name}`}
        onClose={closeChat}
        onResize={(width) => setChat((current) => ({ ...current, width }))}
      >
        <QuestionPanel
          key={target.id}
          api={api}
          targetId={String(target.id)}
          targetName={target.name}
          platformLabel={platformLabel}
          reviewCount={reviewCount}
          collecting={isProcessing}
          onCollect={collect}
          onClose={closeChat}
          onShowReview={showReview}
        />
      </ChatDock>

      {!chat.open && (
        <button
          type="button"
          onClick={() => setChat((current) => ({ ...current, open: true }))}
          aria-label="Open ReviewLens chat"
          className="fixed bottom-6 right-6 z-30 flex items-center gap-2 rounded-full bg-indigo-600 px-5 py-3 text-sm font-semibold text-white shadow-lg transition hover:-translate-y-0.5 hover:bg-indigo-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
        >
          <span aria-hidden="true" className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-white/70" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-white" />
          </span>
          Ask about {target.name}
        </button>
      )}
    </div>
  );
}
