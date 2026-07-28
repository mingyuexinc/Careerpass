"""Public, non-sensitive contracts for candidate preparation resources."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

ParseStatus = Literal["processing", "succeeded", "failed"]
DocumentType = Literal["certificate", "strategy", "other"]


class ResumeCreated(BaseModel):
    resume_id: UUID
    parse_status: Literal["processing"] = "processing"


class ResumeListItem(BaseModel):
    resume_id: UUID
    name: str
    type: Literal["resume"] = "resume"
    parse_status: ParseStatus
    created_at: datetime
    failure_code: str | None = None


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

