import { useEffect, useState } from "react";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import ErrorMessage from "../components/ErrorMessage";
import LoadingIndicator from "../components/LoadingIndicator";

/** Protected placeholder. S1-017 replaces the body with the target list. */
export default function TargetsPage() {
  const { api } = useAuth();
  const [email, setEmail] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    api
      .request<{ email: string | null }>("/api/me")
      .then((me) => active && setEmail(me.email ?? "your account"))
      .catch((caught) => {
        if (!active) return;
        setError(
          caught instanceof ApiError
            ? caught.message
            : "Something went wrong on our side. Please try again.",
        );
      });
    return () => {
      active = false;
    };
  }, [api]);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Your targets</h1>
      {error && <ErrorMessage message={error} />}
      {!error && !email && <LoadingIndicator />}
      {email && <p className="text-sm text-slate-600">Verified as {email}.</p>}
    </div>
  );
}
