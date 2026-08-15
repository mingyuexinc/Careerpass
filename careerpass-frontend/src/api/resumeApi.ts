import type { Resume, ResumeParseStatus } from "../domain/types";

interface ApiResponse<T> {
  code: number;
  msg: string;
  data: T | null;
}

interface ResumeResponse {
  resume_id: string;
  parse_status: Exclude<ResumeParseStatus, "not_uploaded" | "uploading">;
}

interface ResumeListItemResponse {
  resume_id: string;
  name: string;
  parse_status: Exclude<ResumeParseStatus, "not_uploaded" | "uploading">;
  created_at: string;
}

interface ResumeListResponse {
  list: ResumeListItemResponse[];
  total: number;
  page: number;
  page_size: number;
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

function authorizationHeaders(accessToken: string): HeadersInit {
  return { Authorization: `Bearer ${accessToken}` };
}

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = (await response.json()) as ApiResponse<T>;
  if (!response.ok || payload.data === null) {
    throw new Error(payload.msg || "简历处理失败，请稍后重试。");
  }
  return payload.data;
}

function toResume(item: ResumeListItemResponse, version: number): Resume {
  return {
    id: item.resume_id,
    fileName: item.name,
    uploadedAt: item.created_at,
    parseStatus: item.parse_status,
    version,
  };
}

export async function listResumes(accessToken: string): Promise<Resume[]> {
  const response = await fetch(`${apiBaseUrl}/resumes`, {
    headers: authorizationHeaders(accessToken),
  });
  const data = await parseResponse<ResumeListResponse>(response);
  return data.list.map((item, index) => toResume(item, data.list.length - index));
}

export async function uploadResume(file: File, accessToken: string): Promise<Resume> {
  const body = new FormData();
  body.append("file", file);
  const response = await fetch(`${apiBaseUrl}/resumes`, {
    method: "POST",
    headers: authorizationHeaders(accessToken),
    body,
  });
  const data = await parseResponse<ResumeResponse>(response);
  return {
    id: data.resume_id,
    fileName: file.name,
    uploadedAt: new Date().toISOString(),
    parseStatus: data.parse_status,
    version: 1,
  };
}
