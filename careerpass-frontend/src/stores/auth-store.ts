import { create } from "zustand";
import type { UserProfile, UserRole } from "../domain/types";
import { loginRequest } from "../api/authApi";
import { userFixtures } from "../api/mock/fixtures/users";
import { isMockMode } from "../config/runtime-mode";

interface AuthState {
  user: UserProfile | null;
  accessToken: string | null;
  error: string | null;
  submitting: boolean;
  login: (username: string, password: string, role: UserRole) => Promise<UserProfile>;
  signIn: (role: UserRole) => void;
  signOut: () => void;
}

const AUTH_SESSION_KEY = "careerpass.auth.session";

interface PersistedAuthSession {
  user: UserProfile;
  accessToken: string;
}

function readPersistedSession(): PersistedAuthSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(AUTH_SESSION_KEY);
    if (!raw) return null;
    const session = JSON.parse(raw) as Partial<PersistedAuthSession>;
    if (!session.accessToken || !session.user || !session.user.id || !session.user.role) {
      return null;
    }
    return session as PersistedAuthSession;
  } catch {
    return null;
  }
}

function persistSession(session: PersistedAuthSession): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(AUTH_SESSION_KEY, JSON.stringify(session));
}

function clearPersistedSession(): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(AUTH_SESSION_KEY);
}

const persistedSession = isMockMode() ? null : readPersistedSession();

export const useAuthStore = create<AuthState>((set) => ({
  user: persistedSession?.user ?? null,
  accessToken: persistedSession?.accessToken ?? null,
  error: null,
  submitting: false,
  login: async (username, password, role) => {
    set({ submitting: true, error: null });
    try {
      if (isMockMode()) {
        if (!username.trim() || !password.trim()) {
          throw new Error("请输入账号和密码");
        }
        const mockUser = userFixtures.find((item) => item.role === role);
        if (!mockUser) throw new Error("演示身份不存在");
        set({ user: mockUser, accessToken: null, submitting: false });
        return mockUser;
      }
      const response = await loginRequest(username, password, role);
      const authenticatedUser: UserProfile = {
        id: response.user.user_id,
        role: response.user.active_role,
        displayName: response.user.name ?? response.user.username ?? username,
        title: response.user.active_role === "candidate" ? "求职者工作台" : "HR 工作台",
      };
      persistSession({ user: authenticatedUser, accessToken: response.access_token });
      set({
        user: authenticatedUser,
        accessToken: response.access_token,
        submitting: false,
      });
      return authenticatedUser;
    } catch (error) {
      const message = error instanceof Error ? error.message : "登录失败，请稍后重试";
      set({ submitting: false, error: message });
      throw error;
    }
  },
  signIn: (role) =>
    set({ user: userFixtures.find((item) => item.role === role) ?? null, error: null }),
  signOut: () => {
    clearPersistedSession();
    set({ user: null, accessToken: null, error: null, submitting: false });
  },
}));
