import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "./api";

export function useDashboardStats() {
  return useQuery({
    queryKey: ["dashboard", "stats"],
    queryFn: async () => {
      const { data } = await dashboardApi.stats();
      return data;
    },
    staleTime: 60_000,
  });
}

export function useMyTasks(limit = 20) {
  return useQuery({
    queryKey: ["dashboard", "my-tasks", limit],
    queryFn: async () => {
      const { data } = await dashboardApi.myTasks(limit);
      return data;
    },
  });
}

export function useRecentActivity(limit = 20) {
  return useQuery({
    queryKey: ["dashboard", "recent-activity", limit],
    queryFn: async () => {
      const { data } = await dashboardApi.recentActivity(limit);
      return data;
    },
  });
}
