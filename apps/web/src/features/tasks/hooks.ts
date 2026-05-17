import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { useToast } from "@/components/ui/useToast";
import { parseApiError } from "@/lib/api/errors";
import * as tasksApi from "./api";

export const TASK_KEYS = {
  all: (projectId: string) => ["tasks", projectId] as const,
  list: (projectId: string, params?: object) => ["tasks", projectId, "list", params] as const,
};

export function useTasks(
  projectId: string,
  params?: { page?: number; size?: number; q?: string; status?: string },
) {
  return useQuery({
    queryKey: TASK_KEYS.list(projectId, params),
    queryFn: () => tasksApi.listTasks(projectId, params),
    enabled: !!projectId,
  });
}

export function useCreateTask(projectId: string) {
  const qc = useQueryClient();
  const { toast } = useToast();
  return useMutation({
    mutationFn: (payload: tasksApi.TaskCreate) => tasksApi.createTask(projectId, payload),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: TASK_KEYS.all(projectId) });
      toast({ variant: "success", title: "Task created" });
    },
    onError: (err) => {
      const { message } = parseApiError(err);
      toast({ variant: "error", title: "Failed to create task", description: message });
    },
  });
}

export function useUpdateTask(projectId: string) {
  const qc = useQueryClient();
  const { toast } = useToast();
  return useMutation({
    mutationFn: ({
      taskId,
      payload,
      updatedAt,
    }: {
      taskId: string;
      payload: tasksApi.TaskUpdate;
      updatedAt: string;
    }) => tasksApi.updateTask(taskId, payload, updatedAt),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: TASK_KEYS.all(projectId) });
      toast({ variant: "success", title: "Task updated" });
    },
    onError: (err) => {
      const { message } = parseApiError(err);
      toast({ variant: "error", title: "Failed to update task", description: message });
    },
  });
}

export function useTransitionStatus(projectId: string) {
  const qc = useQueryClient();
  const { toast } = useToast();
  type Vars = { taskId: string; status: tasksApi.TaskStatus; updatedAt: string };
  const mutRef = useRef<{ mutate: (v: Vars) => void } | null>(null);
  const mutation = useMutation({
    mutationFn: ({ taskId, status, updatedAt }: Vars) =>
      tasksApi.transitionStatus(taskId, status, updatedAt),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: TASK_KEYS.all(projectId) });
    },
    onError: (err, variables) => {
      const { message } = parseApiError(err);
      toast({
        variant: "error",
        title: "Failed to update status",
        description: message,
        action: { label: "Retry", onClick: () => mutRef.current?.mutate(variables) },
      });
    },
  });
  useEffect(() => {
    mutRef.current = mutation;
  });
  return mutation;
}

export function useDeleteTask(projectId: string) {
  const qc = useQueryClient();
  const { toast } = useToast();
  const mutRef = useRef<{ mutate: (id: string) => void } | null>(null);
  const mutation = useMutation({
    mutationFn: (taskId: string) => tasksApi.deleteTask(taskId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: TASK_KEYS.all(projectId) });
      toast({ variant: "success", title: "Task deleted" });
    },
    onError: (err, taskId) => {
      const { message } = parseApiError(err);
      toast({
        variant: "error",
        title: "Failed to delete task",
        description: message,
        action: { label: "Retry", onClick: () => mutRef.current?.mutate(taskId) },
      });
    },
  });
  useEffect(() => {
    mutRef.current = mutation;
  });
  return mutation;
}
