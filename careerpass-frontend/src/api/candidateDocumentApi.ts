import type { SupportingDocument, SupportingDocumentUploadResult } from "../domain/types";

interface ApiEnvelope<T> {
  code: number;
  msg: string;
  data: T | null;
}

interface CandidateDocumentApiResult {
  file_name: string;
  result: "created" | "duplicate" | "failed";
  candidate_document_id?: string | null;
  file_type?: "pdf" | "md" | "jpg" | "png" | null;
  upload_status: "success" | "failed";
  uploaded_at?: string | null;
  failure_code?: string | null;
}

interface CandidateDocumentListItem {
  candidate_document_id: string;
  name: string;
  file_type: "pdf" | "md" | "jpg" | "png";
  upload_status: "success";
  created_at: string;
}

interface CandidateDocumentUploadData {
  results: CandidateDocumentApiResult[];
}

interface CandidateDocumentListData {
  list: CandidateDocumentListItem[];
  total: number;
  page: number;
  page_size: number;
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

function authorizationHeaders(accessToken: string): HeadersInit {
  return { Authorization: `Bearer ${accessToken}` };
}

function createIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `s05-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = (await response.json()) as ApiEnvelope<T>;
  if (!response.ok || payload.data === null) {
    throw new Error(payload.msg || "其它资料上传失败，请稍后重试。");
  }
  return payload.data;
}

function fileTypeFromName(fileName: string): SupportingDocument["fileType"] {
  const extension = fileName.split(".").at(-1)?.toLowerCase();
  if (
    extension === "pdf" ||
    extension === "md" ||
    extension === "jpg" ||
    extension === "png"
  ) {
    return extension;
  }
  return "pdf";
}

function toDocument(result: CandidateDocumentApiResult): SupportingDocument | null {
  if (
    !result.candidate_document_id ||
    !result.file_type ||
    !result.uploaded_at ||
    result.upload_status !== "success"
  ) {
    return null;
  }
  return {
    id: result.candidate_document_id,
    fileName: result.file_name,
    fileType: result.file_type,
    uploadedAt: result.uploaded_at,
    status: "success",
  };
}

function toUploadResult(
  result: CandidateDocumentApiResult,
): SupportingDocumentUploadResult {
  return {
    fileName: result.file_name,
    status: result.upload_status,
    result: result.result,
    document: toDocument(result),
    failureCode: result.failure_code ?? null,
  };
}

export async function listCandidateDocuments(
  accessToken: string,
): Promise<SupportingDocument[]> {
  const response = await fetch(`${apiBaseUrl}/candidate_documents`, {
    headers: authorizationHeaders(accessToken),
  });
  const data = await parseResponse<CandidateDocumentListData>(response);
  return data.list.map((item) => ({
    id: item.candidate_document_id,
    fileName: item.name,
    fileType: item.file_type,
    uploadedAt: item.created_at,
    status: "success",
  }));
}

export async function uploadCandidateDocuments(
  files: File[],
  accessToken: string,
): Promise<SupportingDocumentUploadResult[]> {
  if (!files.length) throw new Error("请先选择其它求职资料。");
  const body = new FormData();
  files.forEach((file) => body.append("files", file));
  const response = await fetch(`${apiBaseUrl}/candidate_documents`, {
    method: "POST",
    headers: {
      ...authorizationHeaders(accessToken),
      "Idempotency-Key": createIdempotencyKey(),
    },
    body,
  });
  const data = await parseResponse<CandidateDocumentUploadData>(response);
  if (data.results.length !== files.length) {
    throw new Error("其它资料上传结果不完整，请稍后重试。");
  }
  return data.results.map(toUploadResult);
}

export function createReadyDocumentResult(file: File): SupportingDocumentUploadResult {
  return {
    fileName: file.name,
    status: "ready",
    document: null,
    failureCode: null,
  };
}

export function getDocumentFileType(fileName: string): SupportingDocument["fileType"] {
  return fileTypeFromName(fileName);
}
