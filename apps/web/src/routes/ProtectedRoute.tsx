import { type ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { FullPageSkeleton } from "@/components/ui";
import { useMe } from "@/features/auth/hooks";

interface ProtectedRouteProps {
  children: ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const location = useLocation();
  const { data: user, isLoading, isError } = useMe();

  if (isLoading) return <FullPageSkeleton />;
  if (isError || !user) {
    return <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />;
  }

  return <>{children}</>;
}
