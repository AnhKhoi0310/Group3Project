import { useState, type FormEvent } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { authErrorMessage } from "../auth/authClient";
import Button from "../components/Button";
import ErrorMessage from "../components/ErrorMessage";
import LoadingIndicator from "../components/LoadingIndicator";
import TextField from "../components/TextField";

type Mode = "login" | "register" | "reset";

const COPY = {
  login: { title: "Log in", submit: "Log in" },
  register: { title: "Create your account", submit: "Create account" },
  reset: { title: "Reset your password", submit: "Send reset email" },
};

export default function LoginPage() {
  const { session, client } = useAuth();
  const location = useLocation();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  if (session.status === "loading") return <LoadingIndicator />;
  if (session.status === "signedIn") {
    return <Navigate to={location.state?.from ?? "/targets"} replace />;
  }

  function switchMode(next: Mode) {
    setMode(next);
    setError("");
    setNotice("");
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      if (mode === "login") await client.signIn(email, password);
      if (mode === "register") await client.register(email, password);
      if (mode === "reset") {
        await client.resetPassword(email);
        setNotice("If that email has an account, a reset link is on its way.");
      }
    } catch (caught) {
      setError(authErrorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-sm rounded-lg border border-slate-200 bg-white p-6">
      <h1 className="text-2xl font-semibold">{COPY[mode].title}</h1>
      <form onSubmit={submit} className="mt-6 space-y-4">
        <TextField
          label="Email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
        {mode !== "reset" && (
          <TextField
            label="Password"
            type="password"
            autoComplete={
              mode === "login" ? "current-password" : "new-password"
            }
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        )}
        {error && <ErrorMessage message={error} />}
        {notice && (
          <p role="status" className="text-sm text-slate-600">
            {notice}
          </p>
        )}
        <Button type="submit" disabled={busy} className="w-full">
          {COPY[mode].submit}
        </Button>
      </form>
      <div className="mt-4 flex justify-between text-sm text-indigo-700">
        {mode === "login" ? (
          <>
            <button type="button" onClick={() => switchMode("register")}>
              Create an account
            </button>
            <button type="button" onClick={() => switchMode("reset")}>
              Forgot password?
            </button>
          </>
        ) : (
          <button type="button" onClick={() => switchMode("login")}>
            Back to log in
          </button>
        )}
      </div>
    </div>
  );
}
