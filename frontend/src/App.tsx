import { Link, Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import RequireAuth from "./auth/RequireAuth";
import Button from "./components/Button";
import LoginPage from "./pages/LoginPage";
import TargetsPage from "./pages/TargetsPage";
import TargetWorkspacePage from "./pages/TargetWorkspacePage";

export default function App() {
  const { session, logout } = useAuth();

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <nav
          aria-label="Main"
          className="mx-auto flex h-14 max-w-6xl items-center gap-6 px-6"
        >
          <span className="text-lg font-semibold">ReviewLens AI</span>
          {session.user && (
            <>
              <Link to="/targets" className="text-sm font-medium">
                Targets
              </Link>
              <span className="ml-auto text-sm text-slate-600">
                {session.user.email}
              </span>
              <Button variant="secondary" onClick={logout}>
                Log out
              </Button>
            </>
          )}
        </nav>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/targets"
            element={
              <RequireAuth>
                <TargetsPage />
              </RequireAuth>
            }
          />
          <Route
    path="/targets/:targetId"
    element={
      <RequireAuth>
        <TargetWorkspacePage />
      </RequireAuth>
    }
  />
          <Route path="*" element={<Navigate to="/targets" replace />} />
        </Routes>
      </main>
    </div>
  );
}
