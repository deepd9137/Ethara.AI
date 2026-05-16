import { Link } from "react-router-dom";
import { Button, Card, CardContent, CardHeader, CardTitle, Skeleton } from "@/components/ui";
import { useAuthStore } from "@/store/auth";
import type {
  ActivityItem,
  MyTask,
  MyTasksResponse,
  RecentActivityResponse,
  TaskPriority,
  TaskStatus,
} from "../api";
import type { DashboardStats } from "../api";
import { useDashboardStats, useMyTasks, useRecentActivity } from "../hooks";

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatDueDate(dateStr: string | null): string {
  if (!dateStr) return "No due date";
  const d = new Date(dateStr + "T00:00:00");
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diff = Math.round((d.getTime() - today.getTime()) / 86_400_000);
  if (diff < 0) return `${Math.abs(diff)}d overdue`;
  if (diff === 0) return "Due today";
  if (diff === 1) return "Due tomorrow";
  return `Due in ${diff}d`;
}

function formatAction(action: string): string {
  return action
    .toLowerCase()
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

const STATUS_LABELS: Record<TaskStatus, string> = {
  todo: "To Do",
  in_progress: "In Progress",
  in_review: "In Review",
  done: "Done",
};

const PRIORITY_COLOURS: Record<TaskPriority, string> = {
  critical: "text-red-500",
  high: "text-orange-500",
  medium: "text-yellow-500",
  low: "text-muted",
};

// ── Getting started banner ─────────────────────────────────────────────────────

function GettingStartedBanner() {
  return (
    <Card className="border-primary/30 bg-primary/5">
      <CardContent className="flex flex-col items-center gap-4 py-10 text-center sm:flex-row sm:text-left">
        <div className="bg-primary/10 flex h-12 w-12 shrink-0 items-center justify-center rounded-full text-2xl">
          🚀
        </div>
        <div className="flex-1">
          <p className="text-body font-semibold">
            You&apos;re all set up — create your first project
          </p>
          <p className="text-muted mt-1 text-sm">
            Projects hold tasks and team members. Once you create one, your dashboard will fill in.
          </p>
        </div>
        <Button asChild size="md">
          <Link to="/projects">Create a project</Link>
        </Button>
      </CardContent>
    </Card>
  );
}

// ── Stat card ─────────────────────────────────────────────────────────────────

interface StatCardProps {
  label: string;
  value: number | undefined;
  loading: boolean;
  accent?: string;
}

function StatCard({ label, value, loading, accent }: StatCardProps) {
  return (
    <Card>
      <CardContent className="pt-4">
        {loading ? (
          <Skeleton className="mb-1 h-8 w-16" />
        ) : (
          <p className={`text-3xl font-bold ${accent ?? "text-body"}`}>{value ?? 0}</p>
        )}
        <p className="text-muted text-sm">{label}</p>
      </CardContent>
    </Card>
  );
}

// ── My Tasks ──────────────────────────────────────────────────────────────────

function MyTaskRow({ task }: { task: MyTask }) {
  const dueCls =
    task.due_date && new Date(task.due_date + "T00:00:00") < new Date()
      ? "text-danger"
      : "text-muted";

  return (
    <div className="border-border flex items-start gap-3 border-b py-3 last:border-0">
      <div className="min-w-0 flex-1">
        <p className="text-body truncate text-sm font-medium">{task.title}</p>
        <p className="text-muted truncate text-xs">{task.project.name}</p>
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1">
        <span className={`text-xs font-medium ${PRIORITY_COLOURS[task.priority]}`}>
          {task.priority}
        </span>
        <span className={`text-xs ${dueCls}`}>{formatDueDate(task.due_date)}</span>
        <span className="bg-surface border-border rounded border px-1.5 py-0.5 text-xs">
          {STATUS_LABELS[task.status]}
        </span>
      </div>
    </div>
  );
}

interface MyTasksListProps {
  data: MyTasksResponse | undefined;
  isLoading: boolean;
}

function MyTasksList({ data, isLoading }: MyTasksListProps) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-14 w-full" />
        ))}
      </div>
    );
  }

  if (!data?.items.length) {
    return (
      <div className="py-6 text-center">
        <p className="text-muted text-sm">No tasks assigned to you right now.</p>
        <p className="text-muted mt-1 text-xs">
          Ask a project admin to assign you tasks, or{" "}
          <Link to="/projects" className="text-primary underline-offset-2 hover:underline">
            browse your projects
          </Link>
          .
        </p>
      </div>
    );
  }

  return (
    <div>
      {data.items.map((task) => (
        <MyTaskRow key={task.id} task={task} />
      ))}
      {data.total > data.items.length && (
        <p className="text-muted pt-2 text-center text-xs">
          +{data.total - data.items.length} more
        </p>
      )}
    </div>
  );
}

// ── Recent Activity ───────────────────────────────────────────────────────────

function ActivityRow({ item }: { item: ActivityItem }) {
  return (
    <div className="border-border flex items-start gap-3 border-b py-3 last:border-0">
      <div className="bg-primary/10 mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold uppercase">
        {item.actor_name?.[0] ?? "?"}
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-body text-sm">
          <span className="font-medium">{item.actor_name ?? "Someone"}</span>{" "}
          <span className="text-muted">{formatAction(item.action)}</span>
        </p>
        {item.project_name && <p className="text-muted truncate text-xs">{item.project_name}</p>}
      </div>
      <span className="text-muted shrink-0 text-xs">{formatDate(item.created_at)}</span>
    </div>
  );
}

interface RecentActivityFeedProps {
  data: RecentActivityResponse | undefined;
  isLoading: boolean;
}

function RecentActivityFeed({ data, isLoading }: RecentActivityFeedProps) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  if (!data?.items.length) {
    return (
      <p className="text-muted py-6 text-center text-sm">No recent activity in your projects.</p>
    );
  }

  return (
    <div>
      {data.items.map((item) => (
        <ActivityRow key={item.id} item={item} />
      ))}
      {data.total > data.items.length && (
        <p className="text-muted pt-2 text-center text-xs">
          +{data.total - data.items.length} more
        </p>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

function isEmptyUser(
  stats: DashboardStats | undefined,
  activity: RecentActivityResponse | undefined,
  loading: boolean,
): boolean {
  if (loading) return false;
  return (
    stats?.open === 0 &&
    stats?.overdue === 0 &&
    stats?.due_this_week === 0 &&
    (activity?.total ?? 0) === 0
  );
}

export function DashboardPage() {
  const user = useAuthStore((s) => s.user);
  const { data: stats, isLoading: statsLoading } = useDashboardStats();
  const { data: tasks, isLoading: tasksLoading } = useMyTasks();
  const { data: activity, isLoading: activityLoading } = useRecentActivity();

  const allLoading = statsLoading || activityLoading;
  const showCTA = isEmptyUser(stats, activity, allLoading);

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-body text-2xl font-semibold">
          Welcome back{user?.name ? `, ${user.name}` : ""}
        </h1>
        <p className="text-muted mt-1 text-sm">Here&apos;s what needs your attention.</p>
      </div>

      {/* CTA for empty users */}
      {showCTA && <GettingStartedBanner />}

      {/* Stat cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard label="Open tasks" value={stats?.open} loading={statsLoading} />
        <StatCard
          label="Overdue"
          value={stats?.overdue}
          loading={statsLoading}
          accent={stats?.overdue ? "text-danger" : undefined}
        />
        <StatCard
          label="Due this week"
          value={stats?.due_this_week}
          loading={statsLoading}
          accent={stats?.due_this_week ? "text-yellow-500" : undefined}
        />
      </div>

      {/* Two-column: my tasks + activity */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>My Tasks</CardTitle>
          </CardHeader>
          <CardContent>
            <MyTasksList data={tasks} isLoading={tasksLoading} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <RecentActivityFeed data={activity} isLoading={activityLoading} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
