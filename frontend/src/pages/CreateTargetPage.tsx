import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { createTarget } from "../api/targets";
import { useAuth } from "../auth/AuthContext";
import Button from "../components/Button";
import ErrorMessage from "../components/ErrorMessage";
import TextField from "../components/TextField";

const PLATFORM_LABEL = "Google Maps";
const UNEXPECTED = "Something went wrong on our side. Please try again.";

export default function CreateTargetPage() {
  const { api } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setFieldErrors({});
    setFormError("");
    try {
      const target = await createTarget(api, {
        name: name.trim(),
        source_url: sourceUrl.trim(),
      });
      navigate(`/targets/${target.id}`, { state: { created: true } });
    } catch (caught) {
      if (caught instanceof ApiError) {
        if (Object.keys(caught.fieldErrors).length > 0) {
          setFieldErrors(caught.fieldErrors);
        } else {
          setFormError(caught.message);
        }
      } else {
        setFormError(UNEXPECTED);
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">New target</h1>
      <form
        onSubmit={submit}
        noValidate
        className="max-w-xl space-y-5 rounded-lg border border-slate-200 bg-white p-6"
      >
        <TextField
          label="Business or product name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          error={fieldErrors.name}
        />
        <TextField
          label="Platform"
          value={PLATFORM_LABEL}
          readOnly
          hint="ReviewLens currently supports Google Maps."
        />
        <TextField
          label="Google Maps link"
          type="text"
          inputMode="url"
          value={sourceUrl}
          onChange={(event) => setSourceUrl(event.target.value)}
          error={fieldErrors.source_url}
          hint="Paste the Google Maps URL of the place you want to analyze."
        />
        {formError && <ErrorMessage message={formError} />}
        <div className="flex items-center gap-3">
          <Button type="submit" disabled={busy}>
            {busy ? "Creating…" : "Create target"}
          </Button>
          <Link to="/targets" className="text-sm font-medium text-indigo-700">
            Cancel
          </Link>
        </div>
      </form>
    </div>
  );
}
