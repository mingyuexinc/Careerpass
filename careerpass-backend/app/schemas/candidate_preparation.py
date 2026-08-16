"""Public, non-sensitive contracts for candidate preparation resources."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

ParseStatus = Literal["processing", "succeeded", "failed"]
UploadStatus = Literal["ready", "success", "failed"]
DocumentUploadResult = Literal["created", "duplicate", "failed"]
ParseFailureCode = Literal[
    "unsupported_file",
    "file_unreadable",
    "storage_unavailable",
    "parser_timeout",
    "schema_validation_failed",
    "internal_error",
]
DocumentFailureCode = Literal[
    "empty_file",
    "unsupported_file",
    "file_too_large",
    "storage_unavailable",
    "internal_error",
]


class ResumeCreated(BaseModel):
    resume_id: UUID
    parse_status: ParseStatus = "processing"


class ResumeListItem(BaseModel):
    resume_id: UUID
    name: str
    type: Literal["resume"] = "resume"
    parse_status: ParseStatus
    failure_code: ParseFailureCode | None = None
    created_at: datetime


class ResumeListResponse(BaseModel):
    list: list[ResumeListItem]
    total: int
    page: int
    page_size: int


class CandidateDocumentUploadResult(BaseModel):
    file_name: str
    result: DocumentUploadResult
    candidate_document_id: UUID | None = None
    file_type: Literal["pdf", "md", "jpg", "png"] | None = None
    upload_status: UploadStatus
    uploaded_at: datetime | None = None
    failure_code: DocumentFailureCode | None = None


class CandidateDocumentUploadResponse(BaseModel):
    results: list[CandidateDocumentUploadResult]


class CandidateDocumentListItem(BaseModel):
    candidate_document_id: UUID
    name: str
    file_type: Literal["pdf", "md", "jpg", "png"]
    upload_status: Literal["success"] = "success"
    created_at: datetime


class CandidateDocumentListResponse(BaseModel):
    list: list[CandidateDocumentListItem]
    total: int
    page: int
    page_size: int
