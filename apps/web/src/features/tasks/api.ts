import { api } from "@/lib/api/client";

export type TaskStatus = "todo" | "in_progress" | "in_review" | "done";
export type TaskPriority = "low" | "medium" | "high" | "critical";

export interface TaskResponse {
  id: string;
  project_id: string;
  creator_id: string;
  assignee_id: string | null;
  title: string;
  description: string;
  status: TaskStatus;
  priority: TaskPriority;
  due_date: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskListResponse {
  items: TaskResponse[];
  total: number;
  page: number;
  size: number;
}

export interface TaskCreate {
  title: string;
  description?: string;
  priority?: TaskPriority;
  assignee_id?: string | null;
  due_date?: string | null;
}

export interface TaskUpdate {
  title?: string;
  description?: string;
  priority?: TaskPriority;
  assignee_id?: string | null;
  due_date?: string | null;
}

export const ALLOWED_TRANSITIONS: Record<TaskStatus, TaskStatus[]> = {
  todo: ["in_progress"],
  in_progress: ["todo", "in_review"],
  in_review: ["done", "in_progress"],
  done: ["in_review"],
};

export async function listTasks(
  projectId: string,
  params?: { page?: number; size?: number; q?: string; status?: string },
): Promise<TaskListResponse> {
  const { data } = await api.get<TaskListResponse>(`/projects/${projectId}/tasks`, { params });
  return data;
}

export async function createTask(projectId: string, payload: TaskCreate): Promise<TaskResponse> {
  const { data } = await api.post<TaskResponse>(`/projects/${projectId}/tasks`, payload);
  return data;
}

export async function updateTask(
  taskId: string,
  payload: TaskUpdate,
  updatedAt: string,
): Promise<TaskResponse> {
  const { data } = await api.patch<TaskResponse>(`/tasks/${taskId}`, payload, {
    headers: { "If-Match": `"${updatedAt}"` },
  });
  return data;
}

export async function transitionStatus(
  taskId: string,
  status: TaskStatus,
  updatedAt: string,
): Promise<TaskResponse> {
  const { data } = await api.patch<TaskResponse>(
    `/tasks/${taskId}/status`,
    { status },
    { headers: { "If-Match": `"${updatedAt}"` } },
  );
  return data;
}

export async function deleteTask(taskId: string): Promise<void> {
  await api.delete(`/tasks/${taskId}`);
}
