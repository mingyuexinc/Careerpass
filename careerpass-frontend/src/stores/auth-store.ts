import { create } from "zustand";
import type { UserProfile, UserRole } from "../domain/types";
import { userFixtures } from "../api/mock/fixtures/users";

interface AuthState {
  user: UserProfile | null;
  signIn: (role: UserRole) => void;
  signOut: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  signIn: (role) =>
    set({ user: userFixtures.find((item) => item.role === role) ?? null }),
  signOut: () => set({ user: null }),
}));
