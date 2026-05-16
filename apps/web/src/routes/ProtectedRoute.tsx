import { useEffect, type ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { FullPageSkeleton } from "@/components/ui";
import { useMe } from "@/features/auth/hooks";
import { useAuthStore } from "@/store/auth";
import { getAccessToken } from "@/lib/auth/token";

interface ProtectedRouteProps {
  children: ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const location = useLocation();
  const { data: user, isLoading, isError } = useMe();
  const setSession = useAuthStore((s) => s.setSession);

  // Sync store whenever /auth/me succeeds — handles the boot hydration case
  // where the in-memory token is empty but the refresh cookie is still valid.
  useEffect(() => {
    if (user) {
      const token = getAccessToken();
      if (token) setSession(user, token);
    }
  }, [user, setSession]);

  if (isLoading) return <FullPageSkeleton />;
  if (isError || !user) {
    return <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />;
  }

  return <>{children}</>;
}
