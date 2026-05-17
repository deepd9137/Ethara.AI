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

export function ProjectCardSkeleton() {
  return (
    <div aria-hidden="true" className="border-border bg-surface rounded-lg border p-4 shadow-sm">
      <Skeleton className="mb-2 h-5 w-3/4" />
      <Skeleton className="mb-4 h-4 w-full" />
      <Skeleton className="h-3 w-1/3" />
    </div>
  );
}

export function ProjectListSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div
      aria-label="Loading projects"
      role="status"
      className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
    >
      {Array.from({ length: count }).map((_, i) => (
        <ProjectCardSkeleton key={i} />
      ))}
    </div>
  );
}

export function TaskRowSkeleton() {
  return (
    <div
      aria-hidden="true"
      className="border-border flex items-center gap-3 border-b py-3 last:border-0"
    >
      <div className="min-w-0 flex-1 space-y-1.5">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-3 w-1/2" />
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1.5">
        <Skeleton className="h-5 w-16 rounded-full" />
        <Skeleton className="h-3 w-12" />
      </div>
    </div>
  );
}

export function TaskListSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div aria-label="Loading tasks" role="status">
      {Array.from({ length: count }).map((_, i) => (
        <TaskRowSkeleton key={i} />
      ))}
    </div>
  );
}

export function MemberRowSkeleton() {
  return (
    <div
      aria-hidden="true"
      className="border-border flex items-center gap-3 border-b py-3 last:border-0"
    >
      <Skeleton className="h-8 w-8 rounded-full" />
      <div className="min-w-0 flex-1 space-y-1.5">
        <Skeleton className="h-4 w-1/3" />
        <Skeleton className="h-3 w-1/2" />
      </div>
      <Skeleton className="h-5 w-14 rounded-full" />
    </div>
  );
}

export function MemberListSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div aria-label="Loading members" role="status">
      {Array.from({ length: count }).map((_, i) => (
        <MemberRowSkeleton key={i} />
      ))}
    </div>
  );
}
