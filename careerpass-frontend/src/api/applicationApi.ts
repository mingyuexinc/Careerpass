import type { Application, DeliveryProgress } from "../domain/types";

interface ApiEnvelope<T> {
  code: number;
  msg: string;
  data: T | null;
}

interface ApplicationResponse {
  id: string;
  job_id: string;
  candidate_id: string;
  status: DeliveryProgress;
  job_title: string;
  company_name: string | null;
  location: string;
  salary: string;
  match_score: number;
  recommendation_reason: string;
  applied_at: string;
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = (await response.json()) as ApiEnvelope<T>;
  if (!response.ok || payload.data === null) {
    throw new Error(payload.msg || "求职进度加载失败，请稍后重试。");
  }
  return payload.data;
}

export async function listCurrentApplications(
  accessToken: string,
): Promise<Application[]> {
  const response = await fetch(`${apiBaseUrl}/applications/current`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  const data = await parseResponse<{
    applications: ApplicationResponse[];
    total: number;
  }>(response);
  return data.applications.map((value) => ({
    id: value.id,
    jobId: value.job_id,
    candidateId: value.candidate_id,
    jobTitle: value.job_title,
    company: value.company_name ?? "受控岗位",
    location: value.location,
    salary: value.salary,
    status: value.status,
    appliedAt: value.applied_at,
    lastContactAt: null,
    matchScore: value.match_score,
    recommendationReason: value.recommendation_reason,
  }));
}
