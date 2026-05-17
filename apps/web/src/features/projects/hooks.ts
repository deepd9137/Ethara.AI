import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useToast } from "@/components/ui/useToast";
import { parseApiError } from "@/lib/api/errors";
import * as projectsApi from "./api";

export const PROJECT_KEYS = {
  all: ["projects"] as const,
  list: (params?: object) => ["projects", "list", params] as const,
  detail: (id: string) => ["projects", id] as const,
  members: (projectId: string) => ["projects", projectId, "members"] as const,
};

export function useProjects(params?: { page?: number; size?: number; q?: string }) {
  return useQuery({
    queryKey: PROJECT_KEYS.list(params),
    queryFn: () => projectsApi.listProjects(params),
  });
}

export function useProject(id: string) {
  return useQuery({
    queryKey: PROJECT_KEYS.detail(id),
    queryFn: () => projectsApi.getProject(id),
    enabled: !!id,
  });
}

export function useCreateProject() {
  const qc = useQueryClient();
  const { toast } = useToast();
  const navigate = useNavigate();
  return useMutation({
    mutationFn: projectsApi.createProject,
    onSuccess: (project) => {
      void qc.invalidateQueries({ queryKey: PROJECT_KEYS.all });
      toast({ variant: "success", title: "Project created" });
      void navigate(`/projects/${project.id}`);
    },
    onError: (err) => {
      const { message } = parseApiError(err);
      toast({ variant: "error", title: "Failed to create project", description: message });
    },
  });
}

export function useUpdateProject(id: string) {
  const qc = useQueryClient();
  const { toast } = useToast();
  return useMutation({
    mutationFn: (payload: projectsApi.ProjectUpdate) => projectsApi.updateProject(id, payload),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: PROJECT_KEYS.detail(id) });
      void qc.invalidateQueries({ queryKey: PROJECT_KEYS.all });
      toast({ variant: "success", title: "Project updated" });
    },
    onError: (err) => {
      const { message } = parseApiError(err);
      toast({ variant: "error", title: "Failed to update project", description: message });
    },
  });
}

export function useDeleteProject() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { toast } = useToast();
  const mutRef = useRef<{ mutate: (id: string) => void } | null>(null);
  const mutation = useMutation({
    mutationFn: projectsApi.deleteProject,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: PROJECT_KEYS.all });
      toast({ variant: "success", title: "Project deleted" });
      void navigate("/projects");
    },
    onError: (err, projectId) => {
      const { message } = parseApiError(err);
      toast({
        variant: "error",
        title: "Failed to delete project",
        description: message,
        action: { label: "Retry", onClick: () => mutRef.current?.mutate(projectId) },
      });
    },
  });
  useEffect(() => {
    mutRef.current = mutation;
  });
  return mutation;
}

export function useMembers(projectId: string) {
  return useQuery({
    queryKey: PROJECT_KEYS.members(projectId),
    queryFn: () => projectsApi.listMembers(projectId),
    enabled: !!projectId,
  });
}

export function useInviteMember(projectId: string) {
  const qc = useQueryClient();
  const { toast } = useToast();
  return useMutation({
    mutationFn: (payload: { email: string; role: projectsApi.ProjectRole }) =>
      projectsApi.inviteMember(projectId, payload),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: PROJECT_KEYS.members(projectId) });
      toast({ variant: "success", title: "Member invited" });
    },
    onError: (err) => {
      const { message } = parseApiError(err);
      toast({ variant: "error", title: "Failed to invite member", description: message });
    },
  });
}

export function useChangeMemberRole(projectId: string) {
  const qc = useQueryClient();
  const { toast } = useToast();
  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: projectsApi.ProjectRole }) =>
      projectsApi.changeMemberRole(projectId, userId, role),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: PROJECT_KEYS.members(projectId) });
      toast({ variant: "success", title: "Role updated" });
    },
    onError: (err) => {
      const { message } = parseApiError(err);
      toast({ variant: "error", title: "Failed to update role", description: message });
    },
  });
}

export function useRemoveMember(projectId: string) {
  const qc = useQueryClient();
  const { toast } = useToast();
  const mutRef = useRef<{ mutate: (id: string) => void } | null>(null);
  const mutation = useMutation({
    mutationFn: (userId: string) => projectsApi.removeMember(projectId, userId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: PROJECT_KEYS.members(projectId) });
      toast({ variant: "success", title: "Member removed" });
    },
    onError: (err, userId) => {
      const { message } = parseApiError(err);
      toast({
        variant: "error",
        title: "Failed to remove member",
        description: message,
        action: { label: "Retry", onClick: () => mutRef.current?.mutate(userId) },
      });
    },
  });
  useEffect(() => {
    mutRef.current = mutation;
  });
  return mutation;
}
