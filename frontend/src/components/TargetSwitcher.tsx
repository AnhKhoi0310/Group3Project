import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, type ApiClient } from "../api/client";
import { listTargets, type AnalysisTarget } from "../api/targets";

interface Props {
  api: ApiClient;
  activeTargetId: number;
  activeTargetName: string;
}

const UNEXPECTED = "We couldn't load your targets. Please try again.";

export default function TargetSwitcher({
  api,
  activeTargetId,
  activeTargetName,
}: Props) {
  const navigate = useNavigate();
  const [targets, setTargets] = useState<AnalysisTarget[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    setLoading(true);
    setError("");

    listTargets(api)
      .then((items) => {
        if (active) {
          setTargets(Array.isArray(items) ? items : []);
        }
      })
      .catch((caught: unknown) => {
        if (!active) return;

        setError(caught instanceof ApiError ? caught.message : UNEXPECTED);
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [api]);

  function handleChange(nextTargetId: string) {
    if (!nextTargetId || nextTargetId === String(activeTargetId)) {
      return;
    }

    const selectedTarget = targets.find(
      (target) => String(target.id) === nextTargetId,
    );

    // Only navigate to a target returned by the authenticated user's
    // owner-filtered target list.
    if (!selectedTarget) return;

    navigate(`/targets/${selectedTarget.id}`);
  }

  // Keep the current target visible even if the target-list request fails
  // or the list has not finished loading.
  const activeTargetIsListed = targets.some(
    (target) => target.id === activeTargetId,
  );

  return (
    <section
      aria-label="Active analysis target"
      className="rounded-lg border border-slate-200 bg-white p-4"
    >
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Active AnalysisTarget
          </p>
          <p
            data-testid="active-target-name"
            className="font-semibold text-slate-900"
          >
            {activeTargetName}
          </p>
        </div>

        <div className="flex flex-col gap-1">
          <label
            htmlFor="active-target-select"
            className="text-sm font-medium text-slate-700"
          >
            Switch target
          </label>

          <select
            id="active-target-select"
            aria-label="Switch active target"
            value={String(activeTargetId)}
            onChange={(event) => handleChange(event.target.value)}
            disabled={loading || targets.length === 0}
            className="min-w-56 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 disabled:cursor-not-allowed disabled:bg-slate-100"
          >
            {!activeTargetIsListed && (
              <option value={String(activeTargetId)}>{activeTargetName}</option>
            )}

            {targets.map((target) => (
              <option key={target.id} value={String(target.id)}>
                {target.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading && (
        <p role="status" className="mt-2 text-sm text-slate-500">
          Loading your targets…
        </p>
      )}

      {error && (
        <p role="alert" className="mt-2 text-sm text-red-700">
          {error}
        </p>
      )}
    </section>
  );
}
