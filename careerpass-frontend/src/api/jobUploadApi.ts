import { useAuthStore } from "../stores/auth-store";

export type JobUploadOutcome = "created" | "duplicate" | "failed";
export type JobTaskStatus = "queued" | "existing";

export interface JobUploadResult {
  fileName: string;
  outcome: JobUploadOutcome;
  jobId: string | null;
  taskStatus: JobTaskStatus | null;
  errorCode: string | null;
}

interface ApiEnvelope<T> {
  code: number;
  msg: string;
  data: T | null;
}

interface JobUploadApiResult {
  index: number;
  outcome: JobUploadOutcome;
  job_id?: string | null;
  task_status?: JobTaskStatus | null;
  error_code?: string | null;
}

interface JobUploadApiData {
  results: JobUploadApiResult[];
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isJobUploadOutcome(value: unknown): value is JobUploadOutcome {
  return value === "created" || value === "duplicate" || value === "failed";
}

function isJobTaskStatus(value: unknown): value is JobTaskStatus {
  return value === "queued" || value === "existing";
}

function parseApiEnvelope(value: unknown): ApiEnvelope<unknown> {
  if (
    !isRecord(value) ||
    typeof value.code !== "number" ||
    typeof value.msg !== "string" ||
    !(value.data === null || isRecord(value.data))
  ) {
    throw new Error("岗位 JD 上传响应格式异常，请稍后重试。");
  }
  return {
    code: value.code,
    msg: value.msg,
    data: value.data,
  };
}

function parseJobUploadData(value: unknown): JobUploadApiData {
  if (!isRecord(value) || !Array.isArray(value.results)) {
    throw new Error("岗位 JD 上传结果格式异常，请稍后重试。");
  }

  const results = value.results.map((item) => {
    if (
      !isRecord(item) ||
      !Number.isInteger(item.index) ||
      item.index < 0 ||
      !isJobUploadOutcome(item.outcome)
    ) {
      throw new Error("岗位 JD 上传结果格式异常，请稍后重试。");
    }
    return {
      index: item.index,
      outcome: item.outcome,
      job_id: typeof item.job_id === "string" ? item.job_id : null,
      task_status: isJobTaskStatus(item.task_status) ? item.task_status : null,
      error_code: typeof item.error_code === "string" ? item.error_code : null,
    } satisfies JobUploadApiResult;
  });

  return { results };
}

export async function uploadJobsWithApi(files: File[]): Promise<JobUploadResult[]> {
  if (!files.length) throw new Error("请先选择岗位 JD 文件。");

  const accessToken = useAuthStore.getState().accessToken;
  if (!accessToken) throw new Error("登录状态已失效，请重新登录。");

  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));

  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl}/jobs`, {
      method: "POST",
      headers: { Authorization: `Bearer ${accessToken}` },
      body: formData,
    });
  } catch {
    throw new Error("岗位 JD 上传失败，请检查服务是否可用后重试。");
  }

  let payload: ApiEnvelope<unknown>;
  try {
    payload = parseApiEnvelope(await response.json());
  } catch {
    throw new Error("岗位 JD 上传响应异常，请稍后重试。");
  }

  if (!response.ok || payload.data === null) {
    throw new Error(payload.msg || "岗位 JD 上传失败，请稍后重试。");
  }

  const data = parseJobUploadData(payload.data);
  const seenIndexes = new Set<number>();
  data.results.forEach((result) => {
    if (result.index >= files.length || seenIndexes.has(result.index)) {
      throw new Error("岗位 JD 上传结果无法对应文件，请稍后重试。");
    }
    seenIndexes.add(result.index);
  });

  if (seenIndexes.size !== files.length) {
    throw new Error("岗位 JD 上传结果不完整，请稍后重试。");
  }

  return [...data.results]
    .sort((left, right) => left.index - right.index)
    .map((result) => ({
      fileName: files[result.index].name,
      outcome: result.outcome,
      jobId: result.job_id ?? null,
      taskStatus: result.task_status ?? null,
      errorCode: result.error_code ?? null,
    }));
}
