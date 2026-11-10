import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { startIngestion, type IngestionResult } from "../api/ingestions";
import { getTarget, type AnalysisTarget } from "../api/targets";
import { useAuth } from "../auth/AuthContext";
import Button from "../components/Button";
import ErrorMessage from "../components/ErrorMessage";
import LoadingIndicator from "../components/LoadingIndicator";

const PLATFORM_LABELS: Record<string, string> = { google_maps: "Google Maps" };
const UNEXPECTED = "Something went wrong on our side. Please try again.";

function describeResult(result: IngestionResult): string {
  const found = `Found ${result.reviews_found} ${
    result.reviews_found === 1 ? "review" : "reviews"
  } for this target.`;
  if (result.reviews_skipped === 0) return found;
  return `${found} ${result.reviews_skipped} ${
    result.reviews_skipped === 1 ? "was" : "were"
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
  const [result, setResult] = useState<IngestionResult | null>(null);
  const [ingestError, setIngestError] = useState("");

  useEffect(() => {
    if (!targetId) return;
    let active = true;
    setTarget(null);
    setError("");
    setResult(null);
    setIngestError("");
    getTarget(api, targetId)
      .then((item) => active && setTarget(item))
      .catch((caught) => {
        if (!active) return;
        setError(caught instanceof ApiError ? caught.message : UNEXPECTED);
      });
    return () => {
      active = false;
    };
  }, [api, targetId]);

  async function collect() {
    if (!target) return;
    setBusy(true);
    setResult(null);
    setIngestError("");
    try {
      setResult(await startIngestion(api, target.id));
    } catch (caught) {
      setIngestError(caught instanceof ApiError ? caught.message : UNEXPECTED);
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
            {result ? "Reviews found" : "Not started"}
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
        {result && (
          <p role="status" className="text-sm text-slate-700">
            {describeResult(result)}
          </p>
        )}
      </section>
    </div>
  );
}
