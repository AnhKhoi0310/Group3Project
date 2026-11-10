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

const PLATFORM_LABELS: Record<string, string> = { google_maps: "Google Maps" };
const UNEXPECTED = "Something went wrong on our side. Please try again.";

function describeFailure(category: string | null | undefined): string {
  const messages: Record<string, string> = {
    invalid_source: "The saved review link could not be used. Check the link and try again.",
    provider_timeout: "The review source took too long to respond. Try again in a few minutes.",
    provider_quota: "The review collection limit has been reached. Try again later.",
    provider_unavailable: "The review source is unavailable. Try again in a few minutes.",
    persistence_error: "Reviews were collected but could not be saved. Try again.",
  };
  return messages[category ?? ""] ?? "The previous review collection attempt failed. Try again.";
}

function describeAttempt(attempt: IngestionAttempt): string {
  const found = `Found ${attempt.reviews_found} ${
    attempt.reviews_found === 1 ? "review" : "reviews"
  }.`;
  if (attempt.reviews_skipped === 0) return found;
  return `${found} ${attempt.reviews_skipped} ${
    attempt.reviews_skipped === 1 ? "was" : "were"
  } skipped because they had no text or rating.`;
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

  useEffect(() => {
    if (!targetId) return;
    let active = true;
    setTarget(null);
    setError("");
    setAttempt(null);
    setIngestError("");

    async function load() {
      try {
        const item = await getTarget(api, targetId);
        if (!active) return;
        setTarget(item);

        const latest = await getLatestIngestion(api, targetId);
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

  const statusLabel = busy
    ? "Processing"
    : attempt?.status === "succeeded"
      ? "Reviews found"
      : attempt?.status === "failed"
        ? "Failed"
        : "Not started";

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
      <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-6">
        <h2 className="text-lg font-semibold">Review collection</h2>
        <p className="text-sm text-slate-600">
          Status:{" "}
          <span className="rounded-md border border-slate-300 bg-slate-100 px-2 py-0.5 font-medium">
            {statusLabel}
          </span>
        </p>
        <Button onClick={collect} disabled={busy}>
          {busy ? "Collecting reviews…" : "Collect reviews"}
        </Button>
        {busy && (
          <p className="text-sm text-slate-600">
            Collecting reviews from the source. This can take a moment.
          </p>
        )}
        {ingestError && <ErrorMessage message={ingestError} />}
        {attempt?.status === "succeeded" && (
          <p role="status" className="text-sm text-slate-700">
            {describeAttempt(attempt)}
          </p>
        )}
        {attempt?.status === "failed" && (
          <p className="text-sm text-slate-600">
            The last attempt failed. Existing saved reviews have been retained.
          </p>
        )}
      </section>
    </div>
  );
}
