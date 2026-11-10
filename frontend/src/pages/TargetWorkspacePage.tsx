
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import ErrorMessage from "../components/ErrorMessage";
import LoadingIndicator from "../components/LoadingIndicator";

interface AnalysisTarget {
  id: number;
  name: string;
  platform: string;
  source_url: string | null;
}

export default function TargetWorkspacePage() {
  const { targetId } = useParams();
  const { api } = useAuth();

  const [target, setTarget] = useState<AnalysisTarget | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [ingesting, setIngesting] = useState(false);
  const [ingestionMessage, setIngestionMessage] = useState("");

  useEffect(() => {
    let active = true;

    api
      .request<AnalysisTarget>(`/api/targets/${targetId}`)
      .then((data) => {
        if (active) setTarget(data);
      })
      .catch((caught) => {
        if (!active) return;
        setError(
          caught instanceof ApiError
            ? caught.message
            : "Something went wrong. Please try again.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [api, targetId]);

  async function handleIngestion() {
    if (!target || ingesting) return;

    setIngesting(true);
    setIngestionMessage("");

    try {
      const result = await api.request<{ fetched_count: number }>(
        `/api/targets/${target.id}/ingestions`,
        { method: "POST" },
      );

      setIngestionMessage(
        `Successfully fetched ${result.fetched_count} reviews.`,
      );
    } catch (caught) {
      setIngestionMessage(
        caught instanceof ApiError
          ? caught.message
          : "Unable to collect reviews. Please try again.",
      );
    } finally {
      setIngesting(false);
    }
  }

  if (loading) return <LoadingIndicator />;
  if (error) return <ErrorMessage message={error} />;
  if (!target) return <p>Target not found.</p>;

  return (
    <div className="space-y-6">
      <Link to="/targets" className="text-sm text-indigo-600 hover:underline">
        Back to targets
      </Link>

      <h1 className="text-2xl font-semibold">{target.name}</h1>

      <div className="space-y-4 rounded-lg border border-slate-200 bg-white p-6">
        <p>
          <strong>Platform:</strong> {target.platform}
        </p>

        <p>
          <strong>Source:</strong> {target.source_url || "Not provided"}
        </p>

        <p>
          <strong>Ingestion status:</strong>{" "}
          {ingesting ? "Collecting reviews" : "Not started"}
        </p>
      </div>

      <button
        type="button"
        onClick={handleIngestion}
        disabled={ingesting || !target.source_url}
        className="rounded-lg bg-indigo-600 px-4 py-2 text-white disabled:opacity-50"
      >
        {ingesting ? "Collecting reviews..." : "Collect Reviews"}
      </button>

      {ingestionMessage && (
        <p role="status" className="text-sm text-slate-700">
          {ingestionMessage}
        </p>
      )}
    </div>
  );
}
