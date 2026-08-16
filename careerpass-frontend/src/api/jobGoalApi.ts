import type { JobGoal, JobGoalInput } from "../domain/types";

interface ApiEnvelope<T> {
  code: number;
  msg: string;
  data: T | null;
}

interface JobGoalResponse {
  id: string;
  offer_target: number;
  title: string;
  filters: string;
  status: "active" | "achieved" | "abandoned";
  created_at: string;
  updated_at: string;
}

interface CurrentJobGoalData {
  goal: JobGoalResponse | null;
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

function authorizationHeaders(accessToken: string): HeadersInit {
  return {
    Authorization: `Bearer ${accessToken}`,
    "Content-Type": "application/json",
  };
}

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = (await response.json()) as ApiEnvelope<T>;
  if (!response.ok || payload.data === null) {
    throw new Error(payload.msg || "求职目标保存失败，请稍后重试。");
  }
  return payload.data;
}

function toJobGoal(value: JobGoalResponse): JobGoal {
  return {
    id: value.id,
    offerTarget: value.offer_target,
    title: value.title,
    filters: value.filters,
    status: value.status,
    createdAt: value.created_at,
    updatedAt: value.updated_at,
  };
}

export async function getCurrentJobGoal(accessToken: string): Promise<JobGoal | null> {
  const response = await fetch(`${apiBaseUrl}/job_goals/current`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  const data = await parseResponse<CurrentJobGoalData>(response);
  return data.goal ? toJobGoal(data.goal) : null;
}

export async function saveCurrentJobGoal(
  input: JobGoalInput,
  accessToken: string,
): Promise<JobGoal> {
  const response = await fetch(`${apiBaseUrl}/job_goals/current`, {
    method: "PUT",
    headers: authorizationHeaders(accessToken),
    body: JSON.stringify({
      offer_target: input.offerTarget,
      title: input.title,
      filters: input.filters,
    }),
  });
  const data = await parseResponse<{ goal: JobGoalResponse }>(response);
  return toJobGoal(data.goal);
}
