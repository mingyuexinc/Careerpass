"""Public, non-sensitive contracts for candidate preparation resources."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

DocumentType = Literal["certificate", "strategy", "other"]
ParseStatus = Literal["processing", "succeeded", "failed"]
ParseFailureCode = Literal[
    "unsupported_file",
    "file_unreadable",
    "storage_unavailable",
    "parser_timeout",
    "schema_validation_failed",
    "internal_error",
]


class ResumeCreated(BaseModel):
    resume_id: UUID
    parse_status: Literal["processing"] = "processing"


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


class CandidateDocumentCreated(BaseModel):
    candidate_document_id: UUID


class CandidateDocumentListItem(BaseModel):
    candidate_document_id: UUID
    name: str
    type: DocumentType
    created_at: datetime


class CandidateDocumentListResponse(BaseModel):
    list: list[CandidateDocumentListItem]
    total: int
    page: int
    page_size: int
