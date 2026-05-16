import { create } from "zustand";
import { clearAccessToken, setAccessToken } from "@/lib/auth/token";

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  is_active: boolean;
  created_at: string;
}

interface AuthState {
  user: AuthUser | null;
  setSession: (user: AuthUser, accessToken: string) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()((set) => ({
  user: null,

  setSession(user, accessToken) {
    setAccessToken(accessToken);
    set({ user });
  },

  clearAuth() {
    clearAccessToken();
    set({ user: null });
  },
}));
