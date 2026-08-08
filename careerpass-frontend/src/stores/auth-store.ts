import { create } from "zustand";
import type { DemoUser, UserRole } from "../domain/types";
import { demoUsers } from "../api/mock/fixtures/users";

interface AuthState {
  user: DemoUser | null;
  signIn: (role: UserRole) => void;
  signOut: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  signIn: (role) => set({ user: demoUsers.find((item) => item.role === role) ?? null }),
  signOut: () => set({ user: null }),
}));
