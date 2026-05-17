import { api } from "@/lib/api/client";

export interface ProjectResponse {
  id: string;
  owner_id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectListResponse {
  items: ProjectResponse[];
  total: number;
  page: number;
  size: number;
}

export interface ProjectCreate {
  name: string;
  description?: string;
}

export interface ProjectUpdate {
  name?: string;
  description?: string;
}

export type ProjectRole = "admin" | "member";

export interface MemberUserInfo {
  id: string;
  email: string;
  name: string;
}

export interface MemberResponse {
  id: string;
  project_id: string;
  user_id: string;
  role: ProjectRole;
  invited_by: string | null;
  created_at: string;
  user: MemberUserInfo;
}

export interface MemberListResponse {
  items: MemberResponse[];
  total: number;
}

export async function listProjects(params?: {
  page?: number;
  size?: number;
  q?: string;
}): Promise<ProjectListResponse> {
  const { data } = await api.get<ProjectListResponse>("/projects", { params });
  return data;
}

export async function getProject(id: string): Promise<ProjectResponse> {
  const { data } = await api.get<ProjectResponse>(`/projects/${id}`);
  return data;
}

export async function createProject(payload: ProjectCreate): Promise<ProjectResponse> {
  const { data } = await api.post<ProjectResponse>("/projects", payload);
  return data;
}

export async function updateProject(id: string, payload: ProjectUpdate): Promise<ProjectResponse> {
  const { data } = await api.patch<ProjectResponse>(`/projects/${id}`, payload);
  return data;
}

export async function deleteProject(id: string): Promise<void> {
  await api.delete(`/projects/${id}`);
}

export async function listMembers(projectId: string): Promise<MemberListResponse> {
  const { data } = await api.get<MemberListResponse>(`/projects/${projectId}/members`);
  return data;
}

export async function inviteMember(
  projectId: string,
  payload: { email: string; role: ProjectRole },
): Promise<MemberResponse> {
  const { data } = await api.post<MemberResponse>(`/projects/${projectId}/members`, payload);
  return data;
}

export async function changeMemberRole(
  projectId: string,
  userId: string,
  role: ProjectRole,
): Promise<MemberResponse> {
  const { data } = await api.patch<MemberResponse>(`/projects/${projectId}/members/${userId}`, {
    role,
  });
  return data;
}

export async function removeMember(projectId: string, userId: string): Promise<void> {
  await api.delete(`/projects/${projectId}/members/${userId}`);
}
