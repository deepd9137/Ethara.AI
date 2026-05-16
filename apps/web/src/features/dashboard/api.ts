import { api } from "@/lib/api/client";

export interface DashboardStats {
  open: number;
  overdue: number;
  due_this_week: number;
}

export interface MyTaskProject {
  id: string;
  name: string;
}

export type TaskStatus = "todo" | "in_progress" | "in_review" | "done";
export type TaskPriority = "low" | "medium" | "high" | "critical";

export interface MyTask {
  id: string;
  project: MyTaskProject;
  title: string;
  status: TaskStatus;
  priority: TaskPriority;
  due_date: string | null;
}

export interface MyTasksResponse {
  items: MyTask[];
  total: number;
}

export interface ActivityItem {
  id: string;
  actor_name: string | null;
  entity_type: string;
  entity_id: string;
  action: string;
  project_id: string | null;
  project_name: string | null;
  created_at: string;
}

export interface RecentActivityResponse {
  items: ActivityItem[];
  total: number;
}

export const dashboardApi = {
  stats() {
    return api.get<DashboardStats>("/dashboard/stats");
  },
  myTasks(limit = 20) {
    return api.get<MyTasksResponse>(`/dashboard/my-tasks?limit=${limit}`);
  },
  recentActivity(limit = 20) {
    return api.get<RecentActivityResponse>(`/dashboard/recent-activity?limit=${limit}`);
  },
};
