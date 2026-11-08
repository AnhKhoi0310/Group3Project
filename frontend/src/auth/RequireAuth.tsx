import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import LoadingIndicator from "../components/LoadingIndicator";
import { useAuth } from "./AuthContext";

/** User-experience guard only. The backend enforces access (S1-BR-004). */
export default function RequireAuth({ children }: { children: ReactNode }) {
  const { session } = useAuth();
  const location = useLocation();

  if (session.status === "loading") return <LoadingIndicator />;
  if (session.status === "signedOut") {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return children;
}
