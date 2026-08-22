import type {
  Application,
  DeliveryProgress,
  HrApplication,
  MatchingRoundSummary,
} from "../domain/types";

export class ApiRequestError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiRequestError";
  }
}

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

export interface CurrentApplicationsResult {
  applications: Application[];
  matching: MatchingRoundSummary;
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = (await response.json()) as ApiEnvelope<T>;
  if (!response.ok || payload.data === null) {
    throw new ApiRequestError(payload.msg || "求职进度加载失败，请稍后重试。", response.status);
  }
  return payload.data;
}

function hrErrorMessage(status: number): string | null {
  switch (status) {
    case 400:
      return "投递状态输入无效。";
    case 401:
      return "登录已失效，请重新登录。";
    case 403:
      return "当前账号无权访问这条投递记录。";
    case 404:
      return "投递记录不存在或已不可用。";
    case 409:
      return "该投递状态不能回退或修改终态。";
    default:
      return null;
  }
}

async function parseHrResponse<T>(response: Response): Promise<T> {
  try {
    return await parseResponse<T>(response);
  } catch (error) {
    if (error instanceof ApiRequestError) {
      throw new ApiRequestError(
        hrErrorMessage(error.status) ?? error.message,
        error.status,
      );
    }
    throw error;
  }
}

export async function listCurrentApplications(
  accessToken: string,
): Promise<CurrentApplicationsResult> {
  const response = await fetch(`${apiBaseUrl}/applications/current`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  const data = await parseResponse<{
    applications: ApplicationResponse[];
    total: number;
    matching?: {
      active_job_count?: number;
      eligible_job_count?: number;
      pending_job_count?: number;
      failed_job_count?: number;
      evaluated_job_count?: number;
      filtered_out_job_count?: number;
      matched_job_count?: number;
    };
  }>(response);
  const matching = data.matching ?? {};
  return {
    applications: data.applications.map((value) => ({
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
    })),
    matching: {
      activeJobCount: matching.active_job_count ?? 0,
      eligibleJobCount: matching.eligible_job_count ?? 0,
      pendingJobCount: matching.pending_job_count ?? 0,
      failedJobCount: matching.failed_job_count ?? 0,
      evaluatedJobCount: matching.evaluated_job_count ?? 0,
      filteredOutJobCount: matching.filtered_out_job_count ?? 0,
      matchedJobCount: matching.matched_job_count ?? 0,
    },
  };
}

interface HrApplicationResponse {
  id: string;
  job_id: string;
  job_title: string;
  company_name: string | null;
  candidate_name: string;
  status: DeliveryProgress;
}

function mapHrApplication(value: HrApplicationResponse): HrApplication {
  return {
    id: value.id,
    jobId: value.job_id,
    jobTitle: value.job_title,
    companyName: value.company_name,
    candidateName: value.candidate_name,
    status: value.status,
  };
}

export async function listCurrentHrApplications(
  accessToken: string,
): Promise<HrApplication[]> {
  const response = await fetch(`${apiBaseUrl}/applications/hr/current`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  const data = await parseHrResponse<{
    applications: HrApplicationResponse[];
    total: number;
  }>(response);
  return data.applications.map(mapHrApplication);
}

export async function updateCurrentHrApplicationStatus(
  id: string,
  status: DeliveryProgress,
  accessToken: string,
): Promise<HrApplication> {
  const response = await fetch(`${apiBaseUrl}/applications/${id}/status`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ status }),
  });
  const data = await parseHrResponse<HrApplicationResponse>(response);
  return mapHrApplication(data);
}
