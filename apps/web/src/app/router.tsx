/* eslint-disable react-refresh/only-export-components */
import { lazy, Suspense } from "react";
import { createBrowserRouter, Outlet } from "react-router-dom";
import { FullPageSkeleton } from "@/components/ui";
import { ProtectedRoute } from "@/routes/ProtectedRoute";

const LoginPage = lazy(() =>
  import("@/features/auth/pages/LoginPage").then((m) => ({ default: m.LoginPage })),
);
const SignupPage = lazy(() =>
  import("@/features/auth/pages/SignupPage").then((m) => ({ default: m.SignupPage })),
);
const DashboardPage = lazy(() =>
  import("@/features/dashboard/pages/DashboardPage").then((m) => ({
    default: m.DashboardPage,
  })),
);

const AppShell = lazy(() =>
  import("@/components/layout/AppShell").then((m) => ({ default: m.AppShell })),
);

function ProtectedLayout() {
  return (
    <ProtectedRoute>
      <Suspense fallback={<FullPageSkeleton />}>
        <AppShell>
          <Outlet />
        </AppShell>
      </Suspense>
    </ProtectedRoute>
  );
}

export const router = createBrowserRouter([
  {
    path: "/login",
    element: (
      <Suspense fallback={<FullPageSkeleton />}>
        <LoginPage />
      </Suspense>
    ),
  },
  {
    path: "/signup",
    element: (
      <Suspense fallback={<FullPageSkeleton />}>
        <SignupPage />
      </Suspense>
    ),
  },
  {
    element: <ProtectedLayout />,
    children: [
      {
        path: "/",
        element: (
          <Suspense fallback={<FullPageSkeleton />}>
            <DashboardPage />
          </Suspense>
        ),
      },
      {
        path: "/dashboard",
        element: (
          <Suspense fallback={<FullPageSkeleton />}>
            <DashboardPage />
          </Suspense>
        ),
      },
    ],
  },
]);
