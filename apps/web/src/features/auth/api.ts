import { api } from "@/lib/api/client";
import type { AuthUser } from "@/store/auth";

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface SignupResponse {
  user: AuthUser;
  access_token: string;
  token_type: string;
}

export const authApi = {
  signup(body: { email: string; name: string; password: string }) {
    return api.post<SignupResponse>("/auth/signup", body);
  },

  login(body: { email: string; password: string }) {
    return api.post<TokenResponse>("/auth/login", body);
  },

  me() {
    return api.get<AuthUser>("/auth/me");
  },

  logout() {
    return api.post<void>("/auth/logout");
  },

  refresh() {
    return api.post<TokenResponse>("/auth/refresh");
  },
};
