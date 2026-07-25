"""Pydantic v2 response models — typed output, clean OpenAPI, no data leaks."""

from pydantic import BaseModel


class ReviewSummary(BaseModel):
    pr_url: str
    repo: str
    pr_number: int | None
    files: int
    total_findings: int
    high: int
    medium: int
    low: int
    posted: int
    last_reviewed: str | None


class ReviewListResponse(BaseModel):
    total: int
    items: list[ReviewSummary]


class Finding(BaseModel):
    id: int
    file: str
    line: int | None
    severity: str | None
    issue: str | None
    explanation: str | None
    commit_sha: str | None
    posted: bool
    created_at: str | None


class ReviewDetail(BaseModel):
    pr_url: str
    repo: str
    pr_number: int | None
    total_findings: int
    high: int
    medium: int
    low: int
    findings: list[Finding]


class EvalSummary(BaseModel):
    precision: float
    recall: float
    f1: float
    tp: int
    fp: int
    fn: int
    cases: int
    tolerance: int | None = None


class EvalCase(BaseModel):
    id: str
    expected: int
    tp: int
    fp: int
    fn: int


class EvalResponse(BaseModel):
    model: str | None
    full_file_context: bool | None = None
    cross_file_retrieval: bool | None = None
    summary: EvalSummary
    cases: list[EvalCase]
