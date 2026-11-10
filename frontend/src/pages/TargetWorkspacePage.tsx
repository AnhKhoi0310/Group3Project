import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { getTarget, type AnalysisTarget } from "../api/targets";
import { useAuth } from "../auth/AuthContext";
import Button from "../components/Button";
import ErrorMessage from "../components/ErrorMessage";
import LoadingIndicator from "../components/LoadingIndicator";

const PLATFORM_LABELS: Record<string, string> = { google_maps: "Google Maps" };
const UNEXPECTED = "Something went wrong on our side. Please try again.";

export default function TargetWorkspacePage() {
  const { api } = useAuth();
  const { targetId } = useParams();
  const location = useLocation();
  const justCreated =
    (location.state as { created?: boolean } | null)?.created === true;
  const [target, setTarget] = useState<AnalysisTarget | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!targetId) return;
    let active = true;
    setTarget(null);
    setError("");
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
            Not started
          </span>
        </p>
        <Button disabled>Collect reviews</Button>
        <p className="text-sm text-slate-600">
          Collecting reviews isn&apos;t available yet.
        </p>
      </section>
    </div>
  );
}
