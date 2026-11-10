import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError } from "../api/client";
import { listTargets, type AnalysisTarget } from "../api/targets";
import { useAuth } from "../auth/AuthContext";
import ErrorMessage from "../components/ErrorMessage";
import LoadingIndicator from "../components/LoadingIndicator";

const PLATFORM_LABELS: Record<string, string> = { google_maps: "Google Maps" };
const UNEXPECTED = "Something went wrong on our side. Please try again.";

export default function TargetsPage() {
  const { api } = useAuth();
  const [targets, setTargets] = useState<AnalysisTarget[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    listTargets(api)
      .then((items) => active && setTargets(items))
      .catch((caught) => {
        if (!active) return;
        setError(caught instanceof ApiError ? caught.message : UNEXPECTED);
      });
    return () => {
      active = false;
    };
  }, [api]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Your targets</h1>
        <Link
          to="/targets/new"
          className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          New target
        </Link>
      </div>
      {error && <ErrorMessage message={error} />}
      {!error && targets === null && <LoadingIndicator />}
      {targets !== null && targets.length === 0 && (
        <div className="rounded-lg border border-slate-200 bg-white p-6">
          <p className="text-slate-700">
            You don&apos;t have any targets yet. Create one to start collecting
            reviews.
          </p>
        </div>
      )}
      {targets !== null && targets.length > 0 && (
        <ul className="space-y-4">
          {targets.map((target) => (
            <li
              key={target.id}
              className="rounded-lg border border-slate-200 bg-white p-6"
            >
              <h2 className="text-lg font-semibold">
                <Link
                  to={`/targets/${target.id}`}
                  className="text-indigo-700 hover:underline"
                >
                  {target.name}
                </Link>
              </h2>
              <p className="mt-1 text-sm text-slate-600">
                {PLATFORM_LABELS[target.platform] ?? target.platform}
              </p>
              <p
                className="mt-1 truncate text-sm text-slate-600"
                title={target.source_url}
              >
                {target.source_url}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
