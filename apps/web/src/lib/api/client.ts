import axios, { type InternalAxiosRequestConfig } from "axios";
import { clearAccessToken, getAccessToken, setAccessToken } from "@/lib/auth/token";
import { useAuthStore } from "@/store/auth";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  withCredentials: true,
  timeout: 15_000,
});

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Race-safe refresh: concurrent 401s share one in-flight promise
let inflightRefresh: Promise<string | null> | null = null;

export async function refreshAccessToken(): Promise<string | null> {
  inflightRefresh ??= api
    .post<{ access_token: string }>("/auth/refresh")
    .then((r) => {
      setAccessToken(r.data.access_token);
      return r.data.access_token;
    })
    .catch(() => null)
    .finally(() => {
      inflightRefresh = null;
    });
  return inflightRefresh;
}

interface RetryableConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

api.interceptors.response.use(undefined, async (err) => {
  const config = err.config as RetryableConfig | undefined;
  if (err.response?.status === 401 && config && !config._retry) {
    config._retry = true;
    const newToken = await refreshAccessToken();
    if (!newToken) {
      clearAccessToken();
      useAuthStore.getState().clearAuth();
      throw err;
    }
    config.headers.Authorization = `Bearer ${newToken}`;
    return api(config);
  }
  throw err;
});
