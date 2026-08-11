import type { UserRole } from "../domain/types";

interface AuthenticatedUserResponse {
  user_id: string;
  roles: UserRole[];
  active_role: UserRole;
  candidate_id: string | null;
  hr_profile_id: string | null;
  username?: string;
  name?: string | null;
}

interface AuthenticationResponse {
  access_token: string;
  token_type: "Bearer";
  expires_in: number;
  user: AuthenticatedUserResponse;
}

interface ApiResponse<T> {
  code: number;
  msg: string;
  data: T | null;
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

export async function loginRequest(
  username: string,
  password: string,
  activeRole: UserRole,
): Promise<AuthenticationResponse> {
  const response = await fetch(`${apiBaseUrl}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password, active_role: activeRole }),
  });
  const payload = (await response.json()) as ApiResponse<AuthenticationResponse>;
  if (!response.ok || payload.data === null) {
    throw new Error(payload.msg || "登录失败，请检查账号和密码");
  }
  return payload.data;
}
