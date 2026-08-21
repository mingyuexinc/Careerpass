import type { HrJob, HrJobParseStatus } from "../domain/types";
import { ApiRequestError } from "./applicationApi";

interface ApiEnvelope<T> {
  code: number;
  msg: string;
  data: T | null;
}

interface HrJobResponse {
  id: string;
  file_name: string | null;
  job_title: string | null;
  company_name: string | null;
  created_at: string;
  parse_status: HrJobParseStatus | null;
  match_started?: boolean;
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

function isHrJobParseStatus(value: unknown): value is HrJobParseStatus {
  return value === "queued" || value === "running" || value === "succeeded" || value === "failed";
}

function mapHrJob(value: HrJobResponse): HrJob {
  return {
    id: value.id,
    fileName: value.file_name ?? null,
    jobTitle: value.job_title,
    companyName: value.company_name,
    createdAt: value.created_at,
    parseStatus: isHrJobParseStatus(value.parse_status) ? value.parse_status : null,
    matchStarted: value.match_started ?? false,
  };
}

export async function deleteHrJob(jobId: string, accessToken: string): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/jobs/${jobId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  const payload = (await response.json()) as ApiEnvelope<unknown>;
  if (!response.ok || payload.data === null) {
    throw new Error(payload.msg || "岗位 JD 删除失败，请稍后重试。");
  }
}

export async function listCurrentHrJobs(accessToken: string): Promise<HrJob[]> {
  const response = await fetch(`${apiBaseUrl}/jobs/hr/current`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  const payload = (await response.json()) as ApiEnvelope<{
    jobs: HrJobResponse[];
    total: number;
  }>;
  if (!response.ok || payload.data === null) {
    throw new ApiRequestError(payload.msg || "岗位列表加载失败，请稍后重试。", response.status);
  }
  return payload.data.jobs.map(mapHrJob);
}
