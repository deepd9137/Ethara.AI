import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { authApi } from "./api";
import { useAuthStore } from "@/store/auth";
import { queryClient } from "@/lib/query/client";

export function useMe() {
  const setSession = useAuthStore((s) => s.setSession);

  return useQuery({
    queryKey: ["auth", "me"],
    queryFn: async () => {
      const { data } = await authApi.me();
      return data;
    },
    retry: false,
    staleTime: Infinity,
    select: (user) => {
      // Ensure store stays in sync after hydration
      const token = useAuthStore.getState().user ? undefined : null;
      if (token !== undefined) setSession(user, token ?? "");
      return user;
    },
  });
}

export function useLogin() {
  const setSession = useAuthStore((s) => s.setSession);
  const navigate = useNavigate();

  return useMutation({
    mutationFn: async (body: { email: string; password: string }) => {
      const { data: tokenData } = await authApi.login(body);
      const { data: userData } = await authApi.me();
      return { token: tokenData.access_token, user: userData };
    },
    onSuccess({ token, user }) {
      setSession(user, token);
      void queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
      navigate("/dashboard");
    },
  });
}

export function useSignup() {
  const setSession = useAuthStore((s) => s.setSession);
  const navigate = useNavigate();

  return useMutation({
    mutationFn: async (body: { email: string; name: string; password: string }) => {
      const { data } = await authApi.signup(body);
      return data;
    },
    onSuccess(data) {
      setSession(data.user, data.access_token);
      void queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
      navigate("/dashboard");
    },
  });
}

export function useLogout() {
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const navigate = useNavigate();

  return useMutation({
    mutationFn: () => authApi.logout(),
    onSettled() {
      clearAuth();
      queryClient.clear();
      navigate("/login");
    },
  });
}
