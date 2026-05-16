import type { AxiosError } from "axios";
import type { ApiError } from "./types";

export function parseApiError(err: unknown): ApiError {
  const axiosErr = err as AxiosError<{ error: ApiError }>;
  const serverError = axiosErr.response?.data?.error;
  if (serverError?.code) return serverError;
  return { code: "NETWORK_ERROR", message: "An unexpected error occurred" };
}
