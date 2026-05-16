import { type HTMLAttributes } from "react";
import { cn } from "@/lib/utils/cn";

export function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      aria-hidden="true"
      className={cn("bg-border animate-pulse rounded-md", className)}
      {...props}
    />
  );
}

export function FullPageSkeleton() {
  return (
    <div
      aria-label="Loading"
      role="status"
      className="bg-bg flex min-h-screen items-center justify-center"
    >
      <div className="flex flex-col items-center gap-3">
        <div className="border-primary h-8 w-8 animate-spin rounded-full border-2 border-t-transparent" />
        <p className="text-muted text-sm">Loading…</p>
      </div>
    </div>
  );
}
