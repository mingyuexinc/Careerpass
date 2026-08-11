import { create } from "zustand";
import type { UserProfile, UserRole } from "../domain/types";
import { loginRequest } from "../api/authApi";
import { userFixtures } from "../api/mock/fixtures/users";

interface AuthState {
  user: UserProfile | null;
  accessToken: string | null;
  error: string | null;
  submitting: boolean;
  login: (username: string, password: string, role: UserRole) => Promise<UserProfile>;
  signIn: (role: UserRole) => void;
  signOut: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: null,
  error: null,
  submitting: false,
  login: async (username, password, role) => {
    set({ submitting: true, error: null });
    try {
      const response = await loginRequest(username, password, role);
      const authenticatedUser: UserProfile = {
        id: response.user.user_id,
        role: response.user.active_role,
        displayName: response.user.name ?? response.user.username ?? username,
        title: response.user.active_role === "candidate" ? "求职者工作台" : "HR 工作台",
      };
      set({ user: authenticatedUser, accessToken: response.access_token, submitting: false });
      return authenticatedUser;
    } catch (error) {
      const message = error instanceof Error ? error.message : "登录失败，请稍后重试";
      set({ submitting: false, error: message });
      throw error;
    }
  },
  signIn: (role) =>
    set({ user: userFixtures.find((item) => item.role === role) ?? null, error: null }),
  signOut: () => set({ user: null, accessToken: null, error: null, submitting: false }),
}));
