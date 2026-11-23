import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import RequireAuth from "./auth/RequireAuth";
import Button from "./components/Button";
import CreateTargetPage from "./pages/CreateTargetPage";
import LoginPage from "./pages/LoginPage";
import TargetsPage from "./pages/TargetsPage";
import TargetWorkspacePage from "./pages/TargetWorkspacePage";

export default function App() {
  const { session, logout } = useAuth();
  // The analysis workspace uses a wide two-column layout with the chat docked.
  const wide = /^\/targets\/\d+\/?$/.test(useLocation().pathname);
  const width = wide ? "max-w-[100rem]" : "max-w-6xl";

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <nav
          aria-label="Main"
          className={`mx-auto flex h-14 ${width} items-center gap-6 px-6`}
        >
          <span className="text-lg font-semibold">ReviewLens AI</span>
          {session.user && (
            <>
              <Link to="/targets" className="text-sm font-medium">
                Targets
              </Link>
              <Link to="/targets/new" className="text-sm font-medium">
                New target
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
      <main className={`mx-auto ${width} px-6 py-8`}>
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
            path="/targets/new"
            element={
              <RequireAuth>
                <CreateTargetPage />
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
